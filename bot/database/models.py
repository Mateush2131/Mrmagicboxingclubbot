"""
Упрощенные модели данных
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Coach(Base):
    """Модель тренера"""
    __tablename__ = 'coaches'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    students = relationship("Student", back_populates="coach")

class Student(Base):
    """Модель ученика - УПРОЩЕННАЯ!"""
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    group_type = Column(String(50))
    remaining_lessons = Column(Integer, default=0)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    created_at = Column(DateTime, default=datetime.now)
    
    coach = relationship("Coach", back_populates="students")
    attendances = relationship("Attendance", back_populates="student")

class Attendance(Base):
    """Модель посещения"""
    __tablename__ = 'attendances'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    date = Column(DateTime, default=datetime.now)
    marked_by = Column(Integer, ForeignKey('coaches.id'))
    
    student = relationship("Student", back_populates="attendances")