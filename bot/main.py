"""
Главный файл упрощенного бота
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

load_dotenv()

from database.db_manager import init_db
from handlers.start import (
    start, show_main_menu, handle_registration, handle_new_name
)
from handlers.students import (
    show_students_list, add_student_start, add_student_handle,
    show_student_card
)
from handlers.attendance import (
    start_attendance, handle_attendance, handle_attendance_callback,
    restore_lessons_start, handle_restore_input
)
from handlers.payments import (
    sell_start, handle_sell_callback
)
from handlers.settings import (
    show_settings, change_coach, select_coach, 
    add_new_coach_start, handle_new_coach, settings_back
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN в .env файле!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка"""
    await update.message.reply_text(
        "👋 *Mr. Magic Club*\n\n"
        "📋 Мои ученики - список учеников\n"
        "✅ Отметить посещение - отметить кто был\n"
        "➕ Добавить ученика - новый ученик\n"
        "💰 Продать абонемент - продажа занятий\n"
        "⚙️ Настройки - сменить тренера\n\n"
        "/start - главное меню\n"
        "/cancel - отмена",
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена действия"""
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено. Используйте /start")

async def handle_student_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора ученика из списка"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("student_"):
        student_id = int(data.split('_')[1])
        await show_student_card(update, context, student_id)
        await query.message.delete()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений"""
    # Регистрация
    if await handle_registration(update, context):
        return
    if await handle_new_name(update, context):
        return
    
    # Добавление нового тренера
    if await handle_new_coach(update, context):
        return
    
    # Восстановление занятий
    if await handle_restore_input(update, context):
        return
    
    # Добавление ученика
    if await add_student_handle(update, context):
        return
    
    # Отметка посещений
    if await handle_attendance(update, context):
        return
    
    text = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Получено сообщение от {user_id}: {text}")
    
    if text == '📋 Мои ученики':
        await show_students_list(update, context)
    elif text == '✅ Отметить посещение':
        await start_attendance(update, context)
    elif text == '➕ Добавить ученика':
        await add_student_start(update, context)
    elif text == '💰 Продать абонемент':
        await sell_start(update, context)
    elif text == '⚙️ Настройки':
        await show_settings(update, context)
    elif text == '✅ Отметить ещё':
        await start_attendance(update, context)
    elif text == '🔙 Главное меню':
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Используйте кнопки меню 👆")

def main():
    """Запуск бота"""
    logger.info("Инициализация базы данных...")
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Callback handlers - УЧЕНИКИ
    application.add_handler(CallbackQueryHandler(handle_student_selection, pattern="^student_"))
    application.add_handler(CallbackQueryHandler(show_students_list, pattern="^back_to_list$"))
    application.add_handler(CallbackQueryHandler(add_student_start, pattern="^add_student$"))
    
    # Callback handlers - ПОСЕЩЕНИЯ
    application.add_handler(CallbackQueryHandler(handle_attendance_callback, pattern="^att_"))
    application.add_handler(CallbackQueryHandler(restore_lessons_start, pattern="^restore_"))
    
    # Callback handlers - ПРОДАЖИ
    application.add_handler(CallbackQueryHandler(handle_sell_callback, pattern="^sell_"))
    
    # Callback handlers - НАСТРОЙКИ
    application.add_handler(CallbackQueryHandler(show_settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(change_coach, pattern="^change_coach$"))
    application.add_handler(CallbackQueryHandler(select_coach, pattern="^select_coach_"))
    application.add_handler(CallbackQueryHandler(add_new_coach_start, pattern="^add_new_coach$"))
    application.add_handler(CallbackQueryHandler(settings_back, pattern="^settings_back$"))
    
    # Callback handlers - НАВИГАЦИЯ
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    
    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Упрощенный бот Mr. Magic Club запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()