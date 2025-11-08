from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for phone number sharing"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Main keyboard for admin"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            # Category buttons - 3 in one row
            [
                KeyboardButton(text="➕ Kategoriya qo'shish"),
                KeyboardButton(text="📋 Kategoriyalar ro'yxati"),
                KeyboardButton(text="🗑 Kategoriya o'chirish")
            ],
            # Question buttons - 2 in one row
            [
                KeyboardButton(text="❓ Savol qo'shish"),
                KeyboardButton(text="🗑 Savol o'chirish")
            ],
            # Answer/Response buttons - 2 in one row
            [
                KeyboardButton(text="💬 Javob qo'shish"),
                KeyboardButton(text="📝 Javoblar ro'yxati")
            ],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_categories_inline_keyboard(categories: List[Dict], prefix: str = "select") -> InlineKeyboardMarkup:
    """Inline keyboard with categories"""
    buttons = []
    for category in categories:
        buttons.append([
            InlineKeyboardButton(
                text=category['name'],
                callback_data=f"{prefix}_category_{category['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_start_test_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Start test button"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Testni boshlash", callback_data=f"start_test_{category_id}")]
        ]
    )
    return keyboard


def get_answers_keyboard(question_id: int, answers: List[Dict]) -> InlineKeyboardMarkup:
    """Keyboard with answer options"""
    buttons = []
    for answer in answers:
        buttons.append([
            InlineKeyboardButton(
                text=f"{answer['answer_text']} - {answer['value']}",
                callback_data=f"answer_{question_id}_{answer['id']}_{answer['value']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_questions_inline_keyboard(questions: List[Dict]) -> InlineKeyboardMarkup:
    """Inline keyboard with questions for admin to select"""
    buttons = []
    for idx, question in enumerate(questions, 1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{idx}. {question['question_text'][:50]}...",
                callback_data=f"delete_question_{question['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_categories_keyboard() -> InlineKeyboardMarkup:
    """Back to categories button"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Ortga", callback_data="back_to_categories")]
        ]
    )
    return keyboard

