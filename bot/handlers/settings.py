"""
Настройки - смена тренера и добавление нового
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.db_manager import get_session, get_coach_by_telegram_id, get_all_coaches, add_coach
from database.models import Coach
import logging

logger = logging.getLogger(__name__)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать настройки"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
        user = query.from_user
    else:
        message = update.message
        user = update.effective_user
    
    if not message:
        logger.error("message is None!")
        return
    
    coach = get_coach_by_telegram_id(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Сменить тренера", callback_data="change_coach")],
        [InlineKeyboardButton("➕ Добавить нового тренера", callback_data="add_new_coach")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    
    text = f"⚙️ *Настройки*\n\n"
    text += f"👤 Текущий тренер: {coach.full_name if coach else 'не выбран'}\n"
    text += f"🆔 Telegram ID: {user.id}\n"
    
    await message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена тренера - показать список"""
    query = update.callback_query
    await query.answer()
    
    coaches = get_all_coaches()
    
    if not coaches:
        await query.message.edit_text(
            "❌ В системе нет тренеров. Сначала добавьте нового.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Добавить тренера", callback_data="add_new_coach")
            ]])
        )
        return
    
    keyboard = []
    for coach in coaches:
        status = "✅" if coach.telegram_id else "🆓"
        keyboard.append([InlineKeyboardButton(
            f"{status} {coach.full_name}",
            callback_data=f"select_coach_{coach.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить нового", callback_data="add_new_coach")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
    
    await query.message.edit_text(
        "🔄 *Выберите тренера:*\n\n"
        "✅ - уже используется\n"
        "🆓 - свободен",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор нового тренера"""
    query = update.callback_query
    await query.answer()
    
    coach_id = int(query.data.replace("select_coach_", ""))
    user = query.from_user
    telegram_id = user.id
    
    session = get_session()
    try:
        old_coach = session.query(Coach).filter_by(telegram_id=telegram_id).first()
        if old_coach:
            logger.info(f"Отвязываем старого тренера: {old_coach.full_name}")
            old_coach.telegram_id = None
        
        new_coach = session.query(Coach).filter_by(id=coach_id).first()
        if new_coach:
            new_coach.telegram_id = telegram_id
            session.commit()
            
            await query.message.edit_text(
                f"✅ *Тренер изменен!*\n\n"
                f"Теперь вы работаете как: {new_coach.full_name}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text("❌ Тренер не найден")
            
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при смене тренера: {e}")
        await query.message.edit_text("❌ Произошла ошибка")
    finally:
        session.close()
    
    from handlers.start import show_main_menu
    await show_main_menu(update, context)

async def add_new_coach_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление нового тренера"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "👤 *Добавление нового тренера*\n\n"
        "Введите полное имя нового тренера:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data['awaiting_new_coach'] = True

async def handle_new_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени нового тренера"""
    if not context.user_data.get('awaiting_new_coach'):
        return False
    
    new_name = update.message.text.strip()
    user = update.effective_user
    
    if not new_name:
        await update.message.reply_text("Имя не может быть пустым. Введите имя:")
        return True
    
    session = get_session()
    try:
        existing = session.query(Coach).filter_by(full_name=new_name).first()
        if existing:
            await update.message.reply_text(
                f"❌ Тренер '{new_name}' уже существует.\n"
                f"Используйте 'Сменить тренера' чтобы выбрать его.",
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        
        new_coach = Coach(
            telegram_id=None,
            full_name=new_name
        )
        session.add(new_coach)
        session.commit()
        
        logger.info(f"Добавлен новый тренер: {new_name}")
        
        await update.message.reply_text(
            f"✅ *Тренер добавлен!*\n\n"
            f"Имя: {new_name}\n"
            f"Теперь он может войти через /start",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при добавлении тренера: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении")
    finally:
        session.close()
    
    context.user_data.pop('awaiting_new_coach', None)
    
    from handlers.start import show_main_menu
    await show_main_menu(update, context)
    return True

async def settings_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в настройки"""
    query = update.callback_query
    await query.answer()
    await show_settings(update, context)