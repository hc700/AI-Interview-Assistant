from pydantic import BaseModel, EmailStr, Field


# ---------- 认证 ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(default="", max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: int
    email: str | None = None
    phone: str | None = None
    nickname: str
    is_member: bool = False

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    token: str
    user: UserInfo


# ---------- 简历 ----------
class ResumeOut(BaseModel):
    id: int
    file_name: str
    summary: str | None = None
    tech_tags: list | None = None
    uploaded_at: str | None = None
    is_deleted: int = 0


class ResumeParseOut(BaseModel):
    file_name: str
    summary: str | None = None
    tech_tags: list | None = None
    word_count: int = 0


# ---------- 面试会话 ----------
class SessionCreateIn(BaseModel):
    position_id: int
    difficulty: int = Field(ge=1, le=3, default=2)
    duration_min: int = Field(ge=15, le=120, default=45)
    question_mix: dict = Field(default_factory=lambda: {"voice": 6, "coding": 2, "whiteboard": 1})
    resume_id: int | None = None


class DialogueIn(BaseModel):
    content: str
    question_id: int | None = None
    section_id: int | None = None
    followup_no: int = 0


class CodingSubmitIn(BaseModel):
    section_id: int
    question_id: int | None = None
    language: str = "python"
    code: str


class WhiteboardSnapshotIn(BaseModel):
    section_id: int
    content: dict


# ---------- 公开面试接口（游客模式） ----------
class MockReplyIn(BaseModel):
    question: dict
    answer: str = ""
    followup_no: int = 0
    history: list[dict] = Field(default_factory=list)


class RunCodeIn(BaseModel):
    question: dict
    language: str = "python"
    code: str


class EvaluateIn(BaseModel):
    questions: list[dict] = []
    answers: list[str] = []
    # 新版按题分组数据：[{no, section_type, turns:[{speaker,content}], coding:{...}, whiteboard:{...}}]
    qa_groups: list[dict] = []
    coding_pass_rate: float = 0.0
    whiteboard_elements: int = 0


# ---------- 计费 ----------
class OrderCreateIn(BaseModel):
    plan_id: int
    pay_channel: str = "wechat"
