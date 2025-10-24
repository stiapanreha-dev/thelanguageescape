"""
Database models for The Language Escape Bot
SQLAlchemy ORM models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Float, Text, ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class PaymentStatus(enum.Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"


class TaskType(enum.Enum):
    """Task type enumeration"""
    CHOICE = "choice"  # Multiple choice question
    VOICE = "voice"    # Voice recording
    DIALOG = "dialog"  # Interactive dialog


class User(Base):
    """User model"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Access control
    has_access = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Course progress
    current_day = Column(Integer, default=0, nullable=False)  # 0 = not started
    completed_days = Column(Integer, default=0, nullable=False)
    liberation_code = Column(String(50), default='___________', nullable=False)  # Collected letters (11 underscores for LIBERATION)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    course_started_at = Column(DateTime, nullable=True)
    course_completed_at = Column(DateTime, nullable=True)

    # Relationships
    payments = relationship('Payment', back_populates='user', cascade='all, delete-orphan')
    progress = relationship('Progress', back_populates='user', cascade='all, delete-orphan')
    task_results = relationship('TaskResult', back_populates='user', cascade='all, delete-orphan')
    reminders = relationship('Reminder', back_populates='user', cascade='all, delete-orphan')
    certificates = relationship('Certificate', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User {self.telegram_id}: {self.first_name}>"


class Payment(Base):
    """Payment model"""
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # YooKassa data
    payment_id = Column(String(255), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB', nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Payment details
    description = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Payment metadata (extra info)
    payment_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='payments')

    def __repr__(self):
        return f"<Payment {self.payment_id}: {self.status.value}>"


class Progress(Base):
    """Daily progress tracking"""
    __tablename__ = 'progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    day_number = Column(Integer, nullable=False)

    # Progress flags
    video_watched = Column(Boolean, default=False, nullable=False)
    brief_read = Column(Boolean, default=False, nullable=False)
    tasks_completed = Column(Boolean, default=False, nullable=False)

    # Completion stats
    total_tasks = Column(Integer, default=0, nullable=False)
    completed_tasks = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)

    # Code letter for this day
    code_letter = Column(String(1), nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship('User', back_populates='progress')

    def __repr__(self):
        return f"<Progress User:{self.user_id} Day:{self.day_number}>"


class TaskResult(Base):
    """Task completion results"""
    __tablename__ = 'task_results'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    day_number = Column(Integer, nullable=False)
    task_number = Column(Integer, nullable=False)

    # Task details
    task_type = Column(SQLEnum(TaskType), nullable=False)
    task_title = Column(String(500), nullable=True)

    # Results
    is_correct = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=1, nullable=False)
    user_answer = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=True)

    # Voice task specific
    voice_file_id = Column(String(255), nullable=True)
    voice_duration = Column(Float, nullable=True)
    recognized_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship('User', back_populates='task_results')

    def __repr__(self):
        return f"<TaskResult User:{self.user_id} Day:{self.day_number} Task:{self.task_number}>"


class Reminder(Base):
    """Reminder history"""
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    day_number = Column(Integer, nullable=False)

    # Reminder details
    reminder_type = Column(String(50), default='inactive', nullable=False)
    message_text = Column(Text, nullable=True)

    # Status
    sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='reminders')

    def __repr__(self):
        return f"<Reminder User:{self.user_id} Day:{self.day_number}>"


class Certificate(Base):
    """Generated certificates"""
    __tablename__ = 'certificates'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Certificate details
    certificate_code = Column(String(100), unique=True, nullable=False)
    file_path = Column(String(500), nullable=True)
    file_id = Column(String(255), nullable=True)  # Telegram file_id for reuse

    # Course completion data
    completion_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_days = Column(Integer, default=10, nullable=False)
    final_code = Column(String(50), default='LIBERATION', nullable=False)

    # Stats
    total_tasks = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    accuracy = Column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='certificates')

    def __repr__(self):
        return f"<Certificate {self.certificate_code} for User:{self.user_id}>"


class Material(Base):
    """Course materials (videos, PDFs, etc.)"""
    __tablename__ = 'materials'

    id = Column(Integer, primary_key=True)
    day_number = Column(Integer, nullable=False)

    # Material details
    material_type = Column(String(50), nullable=False)  # video, pdf, audio, image
    title = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_id = Column(String(255), nullable=True)  # Telegram file_id
    url = Column(String(1000), nullable=True)  # For external links (YouTube, etc.)

    # Metadata
    duration = Column(Float, nullable=True)  # For videos/audio
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Order
    order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Material Day:{self.day_number} Type:{self.material_type}>"


class Task(Base):
    """Task definitions"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    day_number = Column(Integer, nullable=False)
    task_number = Column(Integer, nullable=False)

    # Task details
    task_type = Column(SQLEnum(TaskType), nullable=False)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # Task data (JSON structure)
    question = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)  # For choice tasks: ["A", "B", "C", "D"]
    correct_answer = Column(String(255), nullable=True)

    # Voice task specific
    voice_prompt = Column(Text, nullable=True)
    voice_keywords = Column(JSON, nullable=True)  # Keywords to check

    # Dialog task specific
    dialog_steps = Column(JSON, nullable=True)  # Multi-step dialog structure

    # Feedback messages
    correct_message = Column(Text, nullable=True)
    incorrect_message = Column(Text, nullable=True)
    hint = Column(Text, nullable=True)

    # Order
    order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Task Day:{self.day_number} #{self.task_number} Type:{self.task_type.value}>"
