"""SQLAlchemy 模型，与 schema.sql 一一对应。"""
from datetime import datetime

from sqlalchemy import (
    BigInteger, CHAR, DateTime, DECIMAL, ForeignKey, Integer,
    JSON, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    register_source: Mapped[str] = mapped_column(String(16), default="email")
    status: Mapped[int] = mapped_column(TINYINT, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class Resume(Base):
    __tablename__ = "resume"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(128), default="")
    file_url: Mapped[str] = mapped_column(String(255), default="")
    parsed_content: Mapped[dict | None] = mapped_column(JSON)
    tech_tags: Mapped[list | None] = mapped_column(JSON)
    is_deleted: Mapped[int] = mapped_column(TINYINT, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(TINYINT, default=1, index=True)
    reference_answer: Mapped[str | None] = mapped_column(Text)
    test_cases: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[int] = mapped_column(TINYINT, default=1)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)


class QuestionTag(Base):
    __tablename__ = "question_tag"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"))
    tag_name: Mapped[str] = mapped_column(String(32), index=True)

    __table_args__ = (UniqueConstraint("question_id", "tag_name", name="uk_q_tag"),)


class Position(Base):
    __tablename__ = "position"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[int] = mapped_column(TINYINT, default=1)


class InterviewSession(Base):
    __tablename__ = "interview_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resume.id"))
    position_id: Mapped[int] = mapped_column(ForeignKey("position.id"))
    difficulty: Mapped[int] = mapped_column(TINYINT, default=2)
    duration_min: Mapped[int] = mapped_column(SmallInteger, default=45)
    question_mix: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="configured", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    overall_score: Mapped[float | None] = mapped_column(DECIMAL(5, 1))
    overall_comment: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SessionSection(Base):
    __tablename__ = "session_section"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), index=True)
    section_type: Mapped[str] = mapped_column(String(16))
    sequence_no: Mapped[int] = mapped_column(TINYINT)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class SessionQuestion(Base):
    __tablename__ = "session_question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("session_section.id"))
    question_id: Mapped[int | None] = mapped_column(ForeignKey("question.id"))
    question_snapshot: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="builtin")
    sequence_no: Mapped[int] = mapped_column(TINYINT, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class InterviewDialogue(Base):
    __tablename__ = "interview_dialogue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("session_section.id"))
    speaker: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CodingSubmission(Base):
    __tablename__ = "coding_submission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_session.id"), index=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("session_section.id", ondelete="CASCADE"))
    session_question_id: Mapped[int | None] = mapped_column(ForeignKey("session_question.id"))
    language: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(Text)
    run_status: Mapped[str] = mapped_column(String(16), default="pending")
    run_result: Mapped[dict | None] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class WhiteboardSnapshot(Base):
    __tablename__ = "whiteboard_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_session.id"))
    section_id: Mapped[int] = mapped_column(
        ForeignKey("session_section.id", ondelete="CASCADE"), index=True)
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SessionEvaluation(Base):
    __tablename__ = "session_evaluation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), unique=True)
    total_score: Mapped[float] = mapped_column(DECIMAL(5, 1))
    overall_comment: Mapped[str] = mapped_column(String(500), default="")
    eval_version: Mapped[str] = mapped_column(String(16), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DimensionEvaluation(Base):
    __tablename__ = "dimension_evaluation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), index=True)
    dimension: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(DECIMAL(5, 1))
    feedback: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("session_id", "dimension", name="uk_session_dim"),)


class QuestionEvaluation(Base):
    __tablename__ = "question_evaluation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), index=True)
    session_question_id: Mapped[int] = mapped_column(
        ForeignKey("session_question.id"), unique=True)
    score: Mapped[float] = mapped_column(DECIMAL(5, 1))
    feedback: Mapped[str | None] = mapped_column(String(500))
    reference_compare: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    period_type: Mapped[str] = mapped_column(String(16))
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    original_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    description: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[int] = mapped_column(TINYINT, default=1)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class PaymentOrder(Base):
    __tablename__ = "payment_order"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plan.id"))
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2))
    pay_channel: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(64))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserSubscription(Base):
    __tablename__ = "user_subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plan.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("payment_order.id"), unique=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    auto_renew: Mapped[int] = mapped_column(TINYINT, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserQuota(Base):
    __tablename__ = "user_quota"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    quota_month: Mapped[str] = mapped_column(CHAR(7))
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    quota_limit: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint("user_id", "quota_month", name="uk_user_month"),)
