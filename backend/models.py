from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@db:5432/rlhf")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    source = Column(String, nullable=True)
    prompt_index = Column(Integer, nullable=True)  # maps to unit test (0-4)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    responses = relationship("Response", back_populates="prompt")

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    model_name = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    prompt = relationship("Prompt", back_populates="responses")
    ratings = relationship("Rating", back_populates="response")
    execution_result = relationship("ExecutionResult", back_populates="response", uselist=False)

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("responses.id"))
    score = Column(Integer)
    user_id = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    response = relationship("Response", back_populates="ratings")

class ExecutionResult(Base):
    __tablename__ = "execution_results"
    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("responses.id"), unique=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    tests_error = Column(Integer, default=0)
    timed_out = Column(Boolean, default=False)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)
    response = relationship("Response", back_populates="execution_result")

def init_db():
    Base.metadata.create_all(bind=engine)
