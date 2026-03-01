"""
Управление учениками
"""
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.db_manager import get_session, get_coach_by_telegram_id
from database.models import Student
import logging

logger = logging.getLogger(__name__)

# Список групп
GROUPS = [
    "Baby-бокс (4-6 лет)",
    "Средняя группа (7-14 лет)",
    "Взрослые",
    "Девушки",
    "Индивидуально"
]

async def show_students_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список учеников"""
    # Определяем источник вызова
    if update.callback_query:
        user = update.callback_query.from_user
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        user = update.effective_user
        message = update.message
    
    if not message:
        logger.error("message is None!")
        return
    
    coach = get_coach_by_telegram_id(user.id)
    
    if not coach:
        await message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    session = get_session()
    students = session.query(Student).filter_by(coach_id=coach.id).all()
    session.close()
    
    if not students:
        keyboard = [['➕ Добавить ученика'], ['🔙 Главное меню']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await message.reply_text(
            "У вас пока нет учеников. Добавьте первого!",
            reply_markup=reply_markup
        )
        return
    
    text = "📋 *Мои ученики:*\n\n"
    
    for student in students:
        # Цвет в зависимости от остатка
        if student.remaining_lessons < 3:
            emoji = "🔴"
        elif student.remaining_lessons < 8:
            emoji = "🟡"
        else:
            emoji = "🟢"
        
        text += f"{emoji} *{student.name}*\n"
        text += f"   Осталось: {student.remaining_lessons} | {student.group_type}\n\n"
    
    # Инлайн-кнопки с именами
    keyboard = []
    for student in students:
        keyboard.append([InlineKeyboardButton(
            student.name, 
            callback_data=f"student_{student.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить ученика", callback_data="add_student")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_student_card(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Показать карточку ученика"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    session.close()
    
    if not student:
        await query.message.reply_text("❌ Ученик не найден")
        return
    
    # Цвет
    if student.remaining_lessons < 3:
        emoji = "🔴"
    elif student.remaining_lessons < 8:
        emoji = "🟡"
    else:
        emoji = "🟢"
    
    text = f"👤 *{student.name}*\n"
    text += f"📱 {student.phone or 'не указан'}\n"
    text += f"👥 Группа: {student.group_type}\n\n"
    text += f"{emoji} *Осталось занятий: {student.remaining_lessons}*\n\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать абонемент", callback_data=f"sell_student_{student_id}")],
        [InlineKeyboardButton("➕ Восстановить занятия", callback_data=f"restore_{student_id}")],
        [InlineKeyboardButton("🔙 К списку", callback_data="back_to_list")]
    ]
    
    await query.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление ученика"""
    # Определяем источник вызова
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
    
    keyboard = [[g] for g in GROUPS]
    keyboard.append(['🔙 Отмена'])
    
    await message.reply_text(
        "Выберите группу:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    context.user_data['adding_student'] = 'group'

async def add_student_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления ученика"""
    if 'adding_student' not in context.user_data:
        return False
    
    text = update.message.text
    
    if text == '🔙 Отмена':
        from handlers.start import show_main_menu
        await show_main_menu(update, context)
        context.user_data.pop('adding_student', None)
        return True
    
    state = context.user_data['adding_student']
    
    if state == 'group':
        if text not in GROUPS:
            await update.message.reply_text("Выберите группу из списка 👆")
            return True
        
        context.user_data['student_group'] = text
        context.user_data['adding_student'] = 'name'
        await update.message.reply_text("Введите имя ученика:", reply_markup=None)
        return True
    
    elif state == 'name':
        if not text.strip():
            await update.message.reply_text("Имя не может быть пустым")
            return True
        
        context.user_data['student_name'] = text.strip()
        context.user_data['adding_student'] = 'phone'
        
        keyboard = [['Пропустить'], ['🔙 Отмена']]
        await update.message.reply_text(
            "Введите телефон (или Пропустить):",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return True
    
    elif state == 'phone':
        if text != 'Пропустить' and text != '🔙 Отмена':
            context.user_data['student_phone'] = text
        else:
            context.user_data['student_phone'] = None
        
        # Показываем абонементы для выбора
        from handlers.payments import MEMBERSHIPS
        keyboard = [[name] for name in MEMBERSHIPS.keys()]
        keyboard.append(['🔙 Отмена'])
        
        await update.message.reply_text(
            "Выберите абонемент:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        context.user_data['adding_student'] = 'membership'
        return True
    
    elif state == 'membership':
        from handlers.payments import MEMBERSHIPS
        if text not in MEMBERSHIPS.keys():
            await update.message.reply_text("Выберите абонемент из списка 👆")
            return True
        
        membership = MEMBERSHIPS[text]
        user = update.effective_user
        coach = get_coach_by_telegram_id(user.id)
        
        session = get_session()
        try:
            student = Student(
                name=context.user_data['student_name'],
                phone=context.user_data.get('student_phone'),
                group_type=context.user_data['student_group'],
                remaining_lessons=membership['lessons'],
                coach_id=coach.id
            )
            session.add(student)
            session.commit()
            
            await update.message.reply_text(
                f"✅ *Ученик добавлен!*\n\n"
                f"Имя: {student.name}\n"
                f"Группа: {student.group_type}\n"
                f"Занятий: {student.remaining_lessons}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            session.rollback()
            await update.message.reply_text(f"❌ Ошибка: {e}")
        finally:
            session.close()
        
        context.user_data.pop('adding_student', None)
        from handlers.start import show_main_menu
        await show_main_menu(update, context)
        return True
    
    return ы