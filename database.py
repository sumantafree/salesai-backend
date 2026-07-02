from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sales_assistant.db"
)

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(200), unique=True, index=True)
    password = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    business_name = Column(String(200))
    owner_name = Column(String(200), default="")
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    website = Column(String(300), default="")
    industry = Column(String(100), default="")
    location = Column(String(200), default="")
    social_links = Column(Text, default="")
    notes = Column(Text, default="")
    score = Column(Integer, default=0)
    tag = Column(String(20), default="COLD")        # HOT / WARM / COLD
    status = Column(String(30), default="NEW")       # NEW / CONTACTED / REPLIED / QUALIFIED / CALL_BOOKED / CLOSED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lead_id = Column(Integer, ForeignKey("leads.id"))
    message_type = Column(String(20))   # email / whatsapp / linkedin
    subject = Column(String(300), default="")
    body = Column(Text)
    status = Column(String(20), default="DRAFT")    # DRAFT / SENT
    created_at = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(200))
    industry = Column(String(100), default="")
    location = Column(String(200), default="")
    tone = Column(String(30), default="friendly")   # formal / friendly / aggressive
    offer = Column(String(200), default="free audit")
    daily_limit = Column(Integer, default=20)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
