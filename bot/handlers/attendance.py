"""
Отметка посещений и восстановление занятий
"""
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.db_manager import get_session, get_coach_by_telegram_id, update_student_lessons, add_attendance
from database.models import Student
import logging

logger = logging.getLogger(__name__)

GROUPS = [
    "Baby-бокс (4-6 лет)",
    "Средняя группа (7-14 лет)",
    "Взрослые",
    "Девушки",
    "Индивидуально"
]

async def start_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать отметку посещений"""
    keyboard = [[g] for g in GROUPS]
    keyboard.append(['🔙 Главное меню'])
    
    await update.message.reply_text(
        "✅ Выберите группу:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    context.user_data['attendance'] = 'select_group'

async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отметки"""
    if 'attendance' not in context.user_data:
        return False
    
    text = update.message.text
    
    if text == '🔙 Главное меню':
        from handlers.start import show_main_menu
        await show_main_menu(update, context)
        context.user_data.pop('attendance', None)
        return True
    
    if context.user_data['attendance'] == 'select_group':
        if text not in GROUPS:
            await update.message.reply_text("Выберите группу из списка 👆")
            return True
        
        user = update.effective_user
        coach = get_coach_by_telegram_id(user.id)
        
        session = get_session()
        students = session.query(Student).filter_by(
            coach_id=coach.id,
            group_type=text
        ).all()
        session.close()
        
        if not students:
            await update.message.reply_text(f"В группе {text} нет учеников")
            return True
        
        context.user_data['attendance'] = 'marking'
        context.user_data['attendance_group'] = text
        context.user_data['attendance_students'] = {s.id: s.name for s in students}
        context.user_data['attendance_index'] = 0
        context.user_data['attendance_results'] = []
        
        await show_next_student(update, context)
        return True
    
    return False

async def show_next_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующего ученика"""
    students = context.user_data['attendance_students']
    index = context.user_data['attendance_index']
    
    student_ids = list(students.keys())
    
    if index >= len(student_ids):
        await show_summary(update, context)
        return
    
    student_id = student_ids[index]
    student_name = students[student_id]
    
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    remaining = student.remaining_lessons if student else 0
    session.close()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Был", callback_data=f"att_yes_{student_id}"),
            InlineKeyboardButton("❌ Не был", callback_data=f"att_no_{student_id}")
        ],
        [InlineKeyboardButton("⏭ Завершить", callback_data="att_finish")]
    ]
    
    # Определяем, откуда вызвана функция
    if update.callback_query:
        # Если из callback - используем bot.send_message
        chat_id = update.callback_query.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👤 *{student_name}*\n"
                 f"Осталось: {remaining}\n"
                 f"Прогресс: {index + 1}/{len(student_ids)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Если из обычного сообщения
        await update.message.reply_text(
            f"👤 *{student_name}*\n"
            f"Осталось: {remaining}\n"
            f"Прогресс: {index + 1}/{len(student_ids)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_attendance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок - и Был и Не был списывают занятие"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "att_finish":
        await query.message.delete()
        await show_summary(update, context)
        return
    
    parts = data.split('_')
    action = parts[1]  # yes или no
    student_id = int(parts[2])
    
    students = context.user_data['attendance_students']
    student_name = students[student_id]
    results = context.user_data['attendance_results']
    
    user = update.effective_user
    coach = get_coach_by_telegram_id(user.id)
    
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    
    if student and student.remaining_lessons > 0:
        # В ЛЮБОМ СЛУЧАЕ списываем 1 занятие
        student.remaining_lessons -= 1
        add_attendance(student_id, coach.id)
        session.commit()
        
        if action == 'yes':
            results.append(f"✅ {student_name} (был, осталось {student.remaining_lessons})")
        else:
            results.append(f"❌ {student_name} (не был, занятие сгорело, осталось {student.remaining_lessons})")
    else:
        results.append(f"⛔ {student_name} (нет занятий)")
    
    session.close()
    
    context.user_data['attendance_results'] = results
    context.user_data['attendance_index'] += 1
    
    await query.message.delete()
    await show_next_student(update, context)

async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать итоги отметки"""
    results = context.user_data.get('attendance_results', [])
    group = context.user_data.get('attendance_group', '')
    
    # Подсчет статистики
    total = len(results)
    present = sum(1 for r in results if "✅" in r)
    absent = sum(1 for r in results if "❌" in r)
    no_lessons = sum(1 for r in results if "⛔" in r)
    
    text = f"📊 *Итоги: {group}*\n\n"
    text += f"👥 Всего учеников: {total}\n"
    text += f"✅ Присутствовало: {present}\n"
    text += f"❌ Отсутствовало: {absent}\n"
    if no_lessons > 0:
        text += f"⛔ Нет занятий: {no_lessons}\n"
    
    text += f"\n*Детали:*\n"
    for r in results:
        text += f"{r}\n"
    
    keyboard = [
        ['✅ Отметить ещё'],
        ['🔙 Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Определяем, откуда вызвана функция
    if update.callback_query:
        # Если из callback - используем bot.send_message
        chat_id = update.callback_query.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        # Удаляем сообщение с последним учеником
        await update.callback_query.message.delete()
    else:
        # Если из обычного сообщения
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # Очищаем данные отметки
    context.user_data.pop('attendance', None)
    context.user_data.pop('attendance_results', None)
    context.user_data.pop('attendance_group', None)
    context.user_data.pop('attendance_students', None)
    context.user_data.pop('attendance_index', None)

# ========== ВОССТАНОВЛЕНИЕ ЗАНЯТИЙ ==========

async def restore_lessons_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать восстановление занятий"""
    query = update.callback_query
    await query.answer()
    
    student_id = int(query.data.replace("restore_", ""))
    context.user_data['restore_student_id'] = student_id
    
    await query.message.reply_text(
        "🔄 Сколько занятий восстановить? (введите число):"
    )

async def handle_restore_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода количества восстанавливаемых занятий"""
    if 'restore_student_id' not in context.user_data:
        return False
    
    try:
        count = int(update.message.text.strip())
        if count <= 0:
            await update.message.reply_text("❌ Введите положительное число")
            return True
        if count > 100:
            await update.message.reply_text("❌ Слишком много (максимум 100)")
            return True
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return True
    
    student_id = context.user_data['restore_student_id']
    user = update.effective_user
    coach = get_coach_by_telegram_id(user.id)
    
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        if not student:
            await update.message.reply_text("❌ Ученик не найден")
            return True
        
        old = student.remaining_lessons
        student.remaining_lessons += count
        
        # Добавляем запись в историю посещений
        add_attendance(student_id, coach.id, note=f"Восстановлено {count} занятий")
        
        session.commit()
        
        await update.message.reply_text(
            f"✅ *Восстановлено {count} занятий*\n\n"
            f"Ученик: {student.name}\n"
            f"Было: {old}\n"
            f"Стало: {student.remaining_lessons}\n"
            f"Причина: пропуски по болезни",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка восстановления: {e}")
        await update.message.reply_text("❌ Ошибка")
    finally:
        session.close()
    
    context.user_data.pop('restore_student_id', None)
    return True