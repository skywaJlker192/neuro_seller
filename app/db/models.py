from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

# ОБЯЗАТЕЛЬНО ДОБАВЬ ЭТО:
class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass

# Дальше идут твои модели:
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    current_niche = Column(String, nullable=True)
    lead_collected = Column(Boolean, default=False)
    messages = relationship("DialogMessage", back_populates="user")

class DialogMessage(Base):
    __tablename__ = "dialog_messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="messages")

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=True)
    interest = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    sent_to_manager = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
