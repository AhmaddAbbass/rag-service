import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    corpora = relationship("Corpus", back_populates="owner", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")


class Corpus(Base):
    __tablename__ = "corpora"

    corpus_id = Column(String, primary_key=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_name = Column(String, nullable=True)
    source_path = Column(String, nullable=False)
    source_sha256 = Column(String, nullable=False)
    source_len_chars = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    latest_success_attempt_id = Column(String, nullable=True)

    owner = relationship("User", back_populates="corpora")
    attempts = relationship("Attempt", back_populates="corpus", cascade="all, delete-orphan")


class Attempt(Base):
    __tablename__ = "attempts"

    attempt_id = Column(String, primary_key=True)
    corpus_id = Column(String, ForeignKey("corpora.corpus_id", ondelete="CASCADE"), nullable=False)
    runner_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    artifacts = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    corpus = relationship("Corpus", back_populates="attempts")
