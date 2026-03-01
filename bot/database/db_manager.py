"""
Упрощенный менеджер базы данных
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Coach, Student, Attendance
import os

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'mr_magic_simple.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

def init_db():
    """Создание таблиц"""
    Base.metadata.create_all(engine)
    print(f"✅ База данных создана: {DB_PATH}")

def get_session():
    """Получить сессию"""
    return Session()

# === РАБОТА С ТРЕНЕРАМИ ===
def get_coach_by_telegram_id(telegram_id):
    session = get_session()
    try:
        return session.query(Coach).filter_by(telegram_id=telegram_id).first()
    finally:
        session.close()

def add_coach(telegram_id, full_name):
    session = get_session()
    try:
        coach = Coach(telegram_id=telegram_id, full_name=full_name)
        session.add(coach)
        session.commit()
        return coach
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        return None
    finally:
        session.close()

def get_all_coaches():
    session = get_session()
    try:
        return session.query(Coach).all()
    finally:
        session.close()

# === РАБОТА С УЧЕНИКАМИ ===
def get_students_by_coach(coach_id):
    session = get_session()
    try:
        return session.query(Student).filter_by(coach_id=coach_id).all()
    finally:
        session.close()

def add_student(name, phone, group_type, remaining_lessons, coach_id):
    session = get_session()
    try:
        student = Student(
            name=name,
            phone=phone,
            group_type=group_type,
            remaining_lessons=remaining_lessons,
            coach_id=coach_id
        )
        session.add(student)
        session.commit()
        return student
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        return None
    finally:
        session.close()

def update_student_lessons(student_id, new_remaining):
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        if student:
            student.remaining_lessons = new_remaining
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        return False
    finally:
        session.close()

def add_attendance(student_id, coach_id, note=None):
    session = get_session()
    try:
        from .models import Attendance
        attendance = Attendance(
            student_id=student_id, 
            marked_by=coach_id
        )
        session.add(attendance)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        return False
    finally:
        session.close()