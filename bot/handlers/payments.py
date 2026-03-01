"""
Продажа абонементов
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.db_manager import get_session, get_coach_by_telegram_id
from database.models import Student
import logging

logger = logging.getLogger(__name__)

# Абонементы с сайта
MEMBERSHIPS = {
    "Разовое индивидуальное": {"lessons": 1, "price": 3000},
    "Разовое групповое": {"lessons": 1, "price": 800},
    "Индивидуальное 5 занятий": {"lessons": 5, "price": 12000},
    "Индивидуальное 10 занятий": {"lessons": 10, "price": 25000},
    "Групповое 12 занятий": {"lessons": 12, "price": 6900},
    "Групповое 72 занятия": {"lessons": 72, "price": 39000}
}

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать продажу"""
    user = update.effective_user
    coach = get_coach_by_telegram_id(user.id)
    
    session = get_session()
    students = session.query(Student).filter_by(coach_id=coach.id).all()
    session.close()
    
    if not students:
        await update.message.reply_text("Сначала добавьте учеников")
        return
    
    keyboard = []
    for s in students:
        keyboard.append([InlineKeyboardButton(s.name, callback_data=f"sell_student_{s.id}")])
    
    await update.message.reply_text(
        "👤 Выберите ученика:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка продажи"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("sell_student_"):
        student_id = int(data.replace("sell_student_", ""))
        context.user_data['sell_student'] = student_id
        
        keyboard = []
        for name in MEMBERSHIPS.keys():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"sell_membership_{name}")])
        
        await query.message.edit_text(
            "🎫 Выберите абонемент:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("sell_membership_"):
        name = data.replace("sell_membership_", "")
        membership = MEMBERSHIPS[name]
        student_id = context.user_data.get('sell_student')
        
        session = get_session()
        student = session.query(Student).filter_by(id=student_id).first()
        
        if student:
            student.remaining_lessons += membership['lessons']
            session.commit()
            
            await query.message.edit_text(
                f"✅ *Продано!*\n\n"
                f"Ученик: {student.name}\n"
                f"Абонемент: {name}\n"
                f"➕ Добавлено: {membership['lessons']} занятий\n"
                f"💰 Сумма: {membership['price']} ₽\n"
                f"Теперь у ученика {student.remaining_lessons} занятий",
                parse_mode=ParseMode.MARKDOWN
            )
        session.close()
        context.user_data.pop('sell_student', None)