from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from keyboards import (
    get_phone_keyboard,
    get_categories_inline_keyboard,
    get_start_test_keyboard,
    get_answers_keyboard,
    get_back_to_categories_keyboard
)
from config import get_settings
import os

settings = get_settings()
client_router = Router()
from utils import send_to_sheet


class TestStates(StatesGroup):
    waiting_for_phone = State()
    taking_test = State()


# Client start command
@client_router.message(CommandStart())
async def client_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Always send welcome message with logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.jpg")
    
    # Check if user already exists
    user = await db.get_user(message.chat.id)
    
    if user and user.get('phone_number'):
        # User already registered - welcome text WITHOUT contact request
        welcome_text = (
            "👋 Xush kelibsiz!\n\n"
            "Bu bot Urolog-androlog Abror Abdullayev nazorati ostida yaratilgan.\n\n"
            "Bu yerda siz erkaklar salomatligi, prostata muammolari va urologik "
            "holatlar haqida aniq, foydali va ishonchli ma'lumotlarni olasiz."
        )
        
        if os.path.exists(logo_path):
            photo = FSInputFile(logo_path)
            await message.answer_photo(
                photo=photo,
                caption=welcome_text
            )
        else:
            await message.answer(welcome_text)
        
        # Show categories
        await show_categories(message)
    else:
        # New user - welcome text WITH contact request
        welcome_text = (
            "👋 Xush kelibsiz!\n\n"
            "Bu bot Urolog-androlog Abror Abdullayev nazorati ostida yaratilgan.\n\n"
            "Bu yerda siz erkaklar salomatligi, prostata muammolari va urologik "
            "holatlar haqida aniq, foydali va ishonchli ma'lumotlarni olasiz.\n\n"
            "Botdan to'liq foydalanish uchun kontaktingizni qoldiring👇🏻"
        )
        
        if os.path.exists(logo_path):
            photo = FSInputFile(logo_path)
            await message.answer_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=get_phone_keyboard()
            )
        else:
            # Fallback to text if logo not found
            await message.answer(
                welcome_text,
                reply_markup=get_phone_keyboard()
            )
        
        await state.set_state(TestStates.waiting_for_phone)


@client_router.message(TestStates.waiting_for_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    contact = message.contact
    
    # Save user to database
    await db.add_user(
        chat_id=message.chat.id,
        phone_number=contact.phone_number,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username
    )
    
    await state.clear()
    
    # Remove the phone sharing keyboard
    await message.answer(
        "✅ Raqamingiz muvaffaqiyatli saqlandi!\n\n"
        "Endi testlarni boshlashingiz mumkin.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await show_categories(message)


async def show_categories(message: Message):
    """Show available test categories"""
    categories = await db.get_all_categories()
    
    if not categories:
        await message.answer(
            "❌ Hozircha testlar mavjud emas.\n"
            "Keyinroq qayta urinib ko'ring."
        )
        return
    
    await message.answer(
        "📋 Mavjud testlar ro'yxati:\n\n"
        "Test turini tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="select")
    )


@client_router.callback_query(F.data.startswith("select_category_"))
async def show_category_info(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[-1])
    category = await db.get_category(category_id)
    
    if not category:
        await callback.message.edit_text("❌ Kategoriya topilmadi")
        await callback.answer()
        return
    
    questions = await db.get_questions_by_category(category_id)
    
    if not questions:
        await callback.message.edit_text(
            f"❌ '{category['name']}' kategoriyasida savollar yo'q",
            reply_markup=get_back_to_categories_keyboard()
        )
        await callback.answer()
        return
    
    description = category.get('description') or "Endi sizga bir nechta oddiy savollar beriladi.\n\nHar bir savolga so'nggi 1 oy ichida sizda bu holat qanchalik tez-tez\n\nkuzatilganini belgilang."
    
    await callback.message.edit_text(
        f"📝 {category['name']}\n\n"
        f"{description}\n\n"
        f"Savollar soni: {len(questions)}",
        reply_markup=get_start_test_keyboard(category_id)
    )
    await callback.answer()


@client_router.callback_query(F.data.startswith("start_test_"))
async def start_test(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[-1])
    
    # Get all questions for this category
    questions = await db.get_questions_by_category(category_id)
    
    if not questions:
        await callback.message.edit_text("❌ Bu testda savollar yo'q")
        await callback.answer()
        return
    
    # Create test session
    session_id = await db.create_test_session(callback.message.chat.id, category_id)
    
    # Initialize test state
    await state.set_state(TestStates.taking_test)
    await state.update_data(
        category_id=category_id,
        session_id=session_id,
        questions=[q['id'] for q in questions],
        current_question_index=0,
        total_score=0
    )
    
    # Show first question
    await show_question(callback.message, state, callback)


async def show_question(message: Message, state: FSMContext, callback: CallbackQuery = None):
    """Show current question with answers"""
    data = await state.get_data()
    questions = data['questions']
    current_index = data['current_question_index']
    
    if current_index >= len(questions):
        # Test completed
        await complete_test(message, state)
        return
    
    question_id = questions[current_index]
    question = await db.get_question(question_id)
    answers = await db.get_answers_by_question(question_id)
    
    if not answers:
        # Skip questions without answers
        await state.update_data(current_question_index=current_index + 1)
        await show_question(message, state)
        return
    
    question_text = f"❓ Savol {current_index + 1}/{len(questions)}\n\n{question['question_text']}"
    
    if callback:
        await callback.message.edit_text(
            question_text,
            reply_markup=get_answers_keyboard(question_id, answers)
        )
    else:
        await message.answer(
            question_text,
            reply_markup=get_answers_keyboard(question_id, answers)
        )


@client_router.callback_query(F.data.startswith("answer_"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    # Parse callback data: answer_{question_id}_{answer_id}_{value}
    parts = callback.data.split("_")
    question_id = int(parts[1])
    answer_id = int(parts[2])
    value = int(parts[3])
    
    data = await state.get_data()
    
    # Save user response
    await db.save_user_response(
        user_chat_id=callback.message.chat.id,
        category_id=data['category_id'],
        question_id=question_id,
        answer_id=answer_id,
        value=value
    )
    
    # Update score
    new_score = data['total_score'] + value
    await state.update_data(
        total_score=new_score,
        current_question_index=data['current_question_index'] + 1
    )
    
    await callback.answer()
    
    # Show next question
    await show_question(callback.message, state, callback)


async def complete_test(message: Message, state: FSMContext):
    """Complete the test and show results"""
    from main import get_bot
    
    data = await state.get_data()
    total_score = data['total_score']
    session_id = data['session_id']
    category_id = data['category_id']
    
    # Update session as completed
    await db.complete_test_session(session_id, total_score)
    
    category = await db.get_category(category_id)
    user = await db.get_user(message.chat.id)
    
    # Get score-based response
    response = await db.get_response_for_score(category_id, total_score)
    
    result_text = f"✅ Test yakunlandi!\n\n"
    result_text += f"📊 Test: {category['name']}\n"
    result_text += f"Umumiy ball: {total_score}\n\n"
    
    if response:
        # Show custom response based on score
        result_text += f"{response['title']}\n\n"
        result_text += f"{response['response_text']}\n\n"
    else:
        # Default response if admin hasn't configured responses
        result_text += "Ushbu natija asosida shifokor sizga tegishli tavsiyalar berishi mumkin.\n\n"
    
    result_text += "Yangi test boshlash uchun /start ni bosing."
    
    await message.edit_text(result_text)
    
    # Send result to channel if configured
    if settings.CHANNEL_CHAT_ID:
        try:
            bot = get_bot()
            
            # Prepare channel message
            channel_message = f"📊 Yangi test natijasi\n\n"
            channel_message += f"👤 Foydalanuvchi:\n"
            
      
            
            send_to_sheet(user['first_name'],user['phone_number'],total_score,user['username'])
            
            # await bot.send_message(
            #     chat_id=settings.CHANNEL_CHAT_ID,
            #     text=channel_message
            # )
        except Exception as e:
            # Log error but don't fail the test completion
            import logging
            logging.error(f"Failed to send result to channel: {e}")
    
    await state.clear()


@client_router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    categories = await db.get_all_categories()
    
    await callback.message.edit_text(
        "📋 Mavjud testlar ro'yxati:\n\n"
        "Test turini tanlang:",
        reply_markup=get_categories_inline_keyboard(categories, prefix="select")
    )
    await callback.answer()


# Command to view test history
@client_router.message(Command("history"))
async def show_history(message: Message):
    history = await db.get_user_test_history(message.chat.id)
    
    if not history:
        await message.answer("📋 Sizda hali test tarixi yo'q")
        return
    
    text = "📊 Test tarixingiz:\n\n"
    for idx, record in enumerate(history[:10], 1):  # Show last 10 tests
        text += f"{idx}. {record['category_name']}\n"
        text += f"   Ball: {record['total_score']}\n"
        text += f"   Sana: {record['completed_at']}\n\n"
    
    await message.answer(text)

