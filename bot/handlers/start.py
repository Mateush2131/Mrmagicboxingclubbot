"""
Регистрация тренера и главное меню
"""
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.db_manager import get_coach_by_telegram_id, add_coach, get_all_coaches, get_session
from database.models import Coach
import logging

logger = logging.getLogger(__name__)

# Список тренеров с сайта (для первого запуска)
INITIAL_COACHES = [
    "Магомед Муртазалиев",
    "Варзарь Иван",
    "Надиров Гапар",
    "Шишман Сергей",
    "Карина Муртазалиева"
]

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    if update.callback_query:
        user = update.callback_query.from_user
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        user = update.effective_user
        message = update.message
    
    coach = get_coach_by_telegram_id(user.id)
    if not coach:
        await message.reply_text("Сначала нужно зарегистрироваться. Напишите /start")
        return
    
    keyboard = [
        ['📋 Мои ученики'],
        ['✅ Отметить посещение'],
        ['➕ Добавить ученика'],
        ['💰 Продать абонемент'],
        ['⚙️ Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await message.reply_text(
        f"👋 *Главное меню*\n\nТренер: {coach.full_name}\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

def registration_keyboard():
    """Клавиатура для выбора тренера"""
    coaches = get_all_coaches()
    keyboard = [[c.full_name] for c in coaches] if coaches else []
    keyboard.append(["➕ Новый тренер"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    coach = get_coach_by_telegram_id(user.id)
    
    if coach:
        await show_main_menu(update, context)
        return
    
    # Если в базе нет тренеров, добавляем начальных
    session = get_session()
    if session.query(Coach).count() == 0:
        for name in INITIAL_COACHES:
            session.add(Coach(full_name=name, telegram_id=None))
        session.commit()
    session.close()
    
    await update.message.reply_text(
        "👋 Добро пожаловать! Выберите своё имя или добавьте новое:",
        reply_markup=registration_keyboard()
    )
    context.user_data['awaiting_registration'] = True

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора имени"""
    if not context.user_data.get('awaiting_registration'):
        return False
    
    text = update.message.text
    user = update.effective_user
    
    if text == "➕ Новый тренер":
        await update.message.reply_text("Введите ваше полное имя:")
        context.user_data['awaiting_new_name'] = True
        context.user_data['awaiting_registration'] = False
        return True
    
    # Проверяем, есть ли такой тренер
    coaches = get_all_coaches()
    for coach in coaches:
        if coach.full_name == text:
            session = get_session()
            coach.telegram_id = user.id
            session.commit()
            session.close()
            
            await update.message.reply_text(f"✅ Добро пожаловать, {text}!")
            await show_main_menu(update, context)
            context.user_data['awaiting_registration'] = False
            return True
    
    await update.message.reply_text("Имя не найдено. Попробуйте ещё раз:", 
                                   reply_markup=registration_keyboard())
    return True

async def handle_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового имени"""
    if not context.user_data.get('awaiting_new_name'):
        return False
    
    new_name = update.message.text.strip()
    user = update.effective_user
    
    coach = add_coach(user.id, new_name)
    if coach:
        await update.message.reply_text(f"✅ Тренер {new_name} добавлен!")
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("❌ Ошибка. Попробуйте позже.")
    
    context.user_data['awaiting_new_name'] = False
    return True