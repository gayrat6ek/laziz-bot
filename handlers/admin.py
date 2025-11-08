from aiogram import Router, F
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from keyboards import (
    get_admin_main_keyboard,
    get_cancel_keyboard,
    get_categories_inline_keyboard,
    get_questions_inline_keyboard
)
from config import get_settings

settings = get_settings()
admin_router = Router()


class IsAdminFilter(BaseFilter):
    """Filter to check if user is admin"""
    async def __call__(self, event) -> bool:
        # Handle both Message and CallbackQuery
        if hasattr(event, 'message'):  # CallbackQuery
            return event.message.chat.id == settings.ADMIN_CHAT_ID
        elif hasattr(event, 'chat'):  # Message
            return event.chat.id == settings.ADMIN_CHAT_ID
        return False


class CategoryStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_description = State()


class QuestionStates(StatesGroup):
    waiting_for_category_selection = State()
    waiting_for_question_text = State()
    waiting_for_answers = State()


class DeleteStates(StatesGroup):
    waiting_for_category_to_delete = State()
    waiting_for_question_category = State()


class ResponseStates(StatesGroup):
    waiting_for_response_category = State()
    waiting_for_score_range = State()
    waiting_for_response_title = State()
    waiting_for_response_text = State()


def is_admin(chat_id: int) -> bool:
    """Check if user is admin"""
    return chat_id == settings.ADMIN_CHAT_ID


# Admin start command
@admin_router.message(Command("start"), IsAdminFilter())
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👨‍💼 Admin paneliga xush kelibsiz!\n\n"
        "Siz botni boshqarishingiz mumkin.",
        reply_markup=get_admin_main_keyboard()
    )


# Create category
@admin_router.message(F.text == "➕ Kategoriya qo'shish", IsAdminFilter())
async def start_create_category(message: Message, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_category_name)
    await message.answer(
        "Kategoriya nomini kiriting:",
        reply_markup=get_cancel_keyboard()
    )


@admin_router.message(CategoryStates.waiting_for_category_name, IsAdminFilter())
async def process_category_name(message: Message, state: FSMContext):
    
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    await state.update_data(category_name=message.text)
    await state.set_state(CategoryStates.waiting_for_category_description)
    await message.answer(
        "Kategoriya tavsifini kiriting (foydalanuvchilarga ko'rsatiladi):",
        reply_markup=get_cancel_keyboard()
    )


@admin_router.message(CategoryStates.waiting_for_category_description, IsAdminFilter())
async def process_category_description(message: Message, state: FSMContext):
    
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    data = await state.get_data()
    category_name = data.get('category_name')
    
    category_id = await db.create_category(category_name, message.text)
    await state.clear()
    
    await message.answer(
        f"✅ Kategoriya muvaffaqiyatli yaratildi!\n\n"
        f"Nom: {category_name}\n"
        f"ID: {category_id}",
        reply_markup=get_admin_main_keyboard()
    )


# List categories
@admin_router.message(F.text == "📋 Kategoriyalar ro'yxati", IsAdminFilter())
async def list_categories(message: Message):
    
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer("❌ Hozircha kategoriyalar yo'q")
        return
    
    text = "📋 Kategoriyalar ro'yxati:\n\n"
    for cat in categories:
        questions = await db.get_questions_by_category(cat['id'])
        text += f"🔹 {cat['name']} (ID: {cat['id']})\n"
        text += f"   Savollar soni: {len(questions)}\n"
        if cat['description']:
            text += f"   Tavsif: {cat['description'][:50]}...\n"
        text += "\n"
    
    await message.answer(text, reply_markup=get_admin_main_keyboard())


# Delete category
@admin_router.message(F.text == "🗑 Kategoriya o'chirish", IsAdminFilter())
async def start_delete_category(message: Message, state: FSMContext):
    
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer("❌ O'chirish uchun kategoriyalar yo'q")
        return
    
    await state.set_state(DeleteStates.waiting_for_category_to_delete)
    await message.answer(
        "O'chirish uchun kategoriyani tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="delete")
    )


@admin_router.callback_query(F.data.startswith("delete_category_"), IsAdminFilter())
async def process_delete_category(callback: CallbackQuery, state: FSMContext):
    
    category_id = int(callback.data.split("_")[-1])
    category = await db.get_category(category_id)
    
    if category:
        await db.delete_category(category_id)
        await callback.message.edit_text(
            f"✅ Kategoriya '{category['name']}' o'chirildi"
        )
    else:
        await callback.message.edit_text("❌ Kategoriya topilmadi")
    
    await state.clear()
    await callback.message.answer("Menyu:", reply_markup=get_admin_main_keyboard())
    await callback.answer()


# Add question
@admin_router.message(F.text == "❓ Savol qo'shish", IsAdminFilter())
async def start_add_question(message: Message, state: FSMContext):
    
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer(
            "❌ Avval kategoriya yarating!",
            reply_markup=get_admin_main_keyboard()
        )
        return
    
    await state.set_state(QuestionStates.waiting_for_category_selection)
    await message.answer(
        "Savol qo'shish uchun kategoriyani tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="add_question")
    )


@admin_router.callback_query(F.data.startswith("add_question_category_"), IsAdminFilter())
async def process_question_category(callback: CallbackQuery, state: FSMContext):
    
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(question_category_id=category_id)
    await state.set_state(QuestionStates.waiting_for_question_text)
    
    await callback.message.edit_text("✅ Kategoriya tanlandi")
    await callback.message.answer(
        "Savol matnini kiriting:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@admin_router.message(QuestionStates.waiting_for_question_text, IsAdminFilter())
async def process_question_text(message: Message, state: FSMContext):
    
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    await state.update_data(question_text=message.text)
    await state.set_state(QuestionStates.waiting_for_answers)
    
    await message.answer(
        "Endi javoblarni kiriting.\n\n"
        "Barcha javoblarni bir xabar ichida kiriting:\n\n"
        "Format: Javob matni | qiymat\n\n"
        "Masalan:\n"
        "Hech qachon | 0\n"
        "Kamdan-kam | 1\n"
        "Ba'zan | 2\n"
        "Tez-tez | 3\n"
        "Ko'p hollarda | 4\n"
        "Har doim | 5",
        reply_markup=get_cancel_keyboard()
    )


@admin_router.message(QuestionStates.waiting_for_answers, IsAdminFilter())
async def process_answers(message: Message, state: FSMContext):
    
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    # Parse all answers at once from multi-line input
    try:
        lines = message.text.strip().split('\n')
        answers = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split("|")
            if len(parts) != 2:
                await message.answer(
                    f"❌ Noto'g'ri format qatorda: {line}\n\n"
                    "To'g'ri format: Javob matni | qiymat"
                )
                return
            
            answer_text = parts[0].strip()
            value = int(parts[1].strip())
            answers.append((answer_text, value))
        
        if not answers:
            await message.answer("❌ Kamida bitta javob kiriting!")
            return
        
        # Get question data
        data = await state.get_data()
        
        # Create question
        question_id = await db.create_question(
            data['question_category_id'],
            data['question_text']
        )
        
        # Create all answers
        for answer_text, value in answers:
            await db.create_answer(question_id, answer_text, value)
        
        await state.clear()
        
        # Show summary
        summary = "\n".join([f"  • {text} - {val}" for text, val in answers])
        await message.answer(
            f"✅ Savol muvaffaqiyatli yaratildi!\n\n"
            f"Savol: {data['question_text']}\n\n"
            f"Javoblar ({len(answers)} ta):\n{summary}",
            reply_markup=get_admin_main_keyboard()
        )
        
    except ValueError as e:
        await message.answer(
            f"❌ Xatolik: Qiymat raqam bo'lishi kerak!\n\n"
            "To'g'ri format:\n"
            "Hech qachon | 0\n"
            "Kamdan-kam | 1"
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


# Delete question
@admin_router.message(F.text == "🗑 Savol o'chirish", IsAdminFilter())
async def start_delete_question(message: Message, state: FSMContext):
    
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer("❌ Kategoriyalar yo'q")
        return
    
    await state.set_state(DeleteStates.waiting_for_question_category)
    await message.answer(
        "Kategoriyani tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="delete_q")
    )


@admin_router.callback_query(F.data.startswith("delete_q_category_"), IsAdminFilter())
async def show_questions_to_delete(callback: CallbackQuery, state: FSMContext):
    
    category_id = int(callback.data.split("_")[-1])
    questions = await db.get_questions_by_category(category_id)
    
    if not questions:
        await callback.message.edit_text("❌ Bu kategoriyada savollar yo'q")
        await state.clear()
        await callback.message.answer("Menyu:", reply_markup=get_admin_main_keyboard())
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "O'chirish uchun savolni tanlang:",
        reply_markup=get_questions_inline_keyboard(questions)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("delete_question_"), IsAdminFilter())
async def process_delete_question(callback: CallbackQuery, state: FSMContext):
    
    question_id = int(callback.data.split("_")[-1])
    question = await db.get_question(question_id)
    
    if question:
        await db.delete_question(question_id)
        await callback.message.edit_text(
            f"✅ Savol o'chirildi:\n{question['question_text']}"
        )
    else:
        await callback.message.edit_text("❌ Savol topilmadi")
    
    await state.clear()
    await callback.message.answer("Menyu:", reply_markup=get_admin_main_keyboard())
    await callback.answer()


@admin_router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi")
    await callback.message.answer("Menyu:", reply_markup=get_admin_main_keyboard())
    await callback.answer()


# Add category response
@admin_router.message(F.text == "💬 Javob qo'shish", IsAdminFilter())
async def start_add_response(message: Message, state: FSMContext):
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer(
            "❌ Avval kategoriya yarating!",
            reply_markup=get_admin_main_keyboard()
        )
        return
    
    await state.set_state(ResponseStates.waiting_for_response_category)
    await message.answer(
        "Javob qo'shish uchun kategoriyani tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="add_response")
    )


@admin_router.callback_query(F.data.startswith("add_response_category_"), IsAdminFilter())
async def process_response_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(response_category_id=category_id)
    await state.set_state(ResponseStates.waiting_for_score_range)
    
    await callback.message.edit_text("✅ Kategoriya tanlandi")
    await callback.message.answer(
        "Ball oralig'ini kiriting.\n\n"
        "Format: min max\n\n"
        "Masalan:\n"
        "0 7\n"
        "8 19\n"
        "20 35",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@admin_router.message(ResponseStates.waiting_for_score_range, IsAdminFilter())
async def process_score_range(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Noto'g'ri format! Ikki raqam kiriting: min max")
            return
        
        min_score = int(parts[0])
        max_score = int(parts[1])
        
        if min_score > max_score:
            await message.answer("❌ Minimal ball maksimal balldan katta bo'lishi mumkin emas!")
            return
        
        await state.update_data(min_score=min_score, max_score=max_score)
        await state.set_state(ResponseStates.waiting_for_response_title)
        
        await message.answer(
            f"✅ Ball oraliği: {min_score}-{max_score}\n\n"
            "Endi javob sarlavhasini kiriting:\n\n"
            "Masalan:\n"
            "🟢 Natija: Yaxshi (0–7 ball)\n"
            "🟡 Natija: O'rta daraja (8–19 ball)",
            reply_markup=get_cancel_keyboard()
        )
    except ValueError:
        await message.answer("❌ Faqat raqamlar kiriting!")


@admin_router.message(ResponseStates.waiting_for_response_title, IsAdminFilter())
async def process_response_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    await state.update_data(response_title=message.text)
    await state.set_state(ResponseStates.waiting_for_response_text)
    
    await message.answer(
        "Javob matnini kiriting:\n\n"
        "Masalan:\n"
        "Sizda prostata bilan bog'liq o'rta darajadagi belgilar aniqlangan.\n\n"
        "Bu holatda muammoni e'tiborsiz qoldirmaslik kerak — chunki vaqt o'tgan sari u og'irlashishi mumkin.",
        reply_markup=get_cancel_keyboard()
    )


@admin_router.message(ResponseStates.waiting_for_response_text, IsAdminFilter())
async def process_response_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=get_admin_main_keyboard())
        return
    
    data = await state.get_data()
    
    # Create response
    await db.create_category_response(
        category_id=data['response_category_id'],
        min_score=data['min_score'],
        max_score=data['max_score'],
        title=data['response_title'],
        response_text=message.text
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ Javob muvaffaqiyatli qo'shildi!\n\n"
        f"Ball oraliği: {data['min_score']}-{data['max_score']}\n"
        f"Sarlavha: {data['response_title']}\n\n"
        f"Matn: {message.text[:100]}...",
        reply_markup=get_admin_main_keyboard()
    )


# List category responses
@admin_router.message(F.text == "📝 Javoblar ro'yxati", IsAdminFilter())
async def list_responses(message: Message, state: FSMContext):
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer("❌ Kategoriyalar yo'q")
        return
    
    await message.answer(
        "Kategoriyani tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="list_responses")
    )


@admin_router.callback_query(F.data.startswith("list_responses_category_"), IsAdminFilter())
async def show_category_responses(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[-1])
    category = await db.get_category(category_id)
    responses = await db.get_category_responses(category_id)
    
    if not responses:
        await callback.message.edit_text(
            f"❌ '{category['name']}' kategoriyasida javoblar yo'q"
        )
        await callback.answer()
        return
    
    text = f"📝 '{category['name']}' kategoriyasi javoblari:\n\n"
    for resp in responses:
        text += f"🔹 Ball: {resp['min_score']}-{resp['max_score']}\n"
        text += f"   {resp['title']}\n"
        text += f"   {resp['response_text'][:50]}...\n\n"
    
    await callback.message.edit_text(text)
    await callback.answer()

