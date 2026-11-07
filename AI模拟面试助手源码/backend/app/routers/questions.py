"""题库与公开面试接口（游客模式不落库，直接调用规则引擎）。"""
import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..ai_engine import evaluate, evaluate_legacy, judge_code, mock_reply
from ..database import get_db
from ..models import Position, Question, QuestionTag
from ..resume_parser import parse_resume
from ..schemas import EvaluateIn, MockReplyIn, ResumeParseOut, RunCodeIn

router = APIRouter(prefix="/api", tags=["questions"])

# 环节 -> 题型映射
_SECTION_TYPE_MAP = {"voice": ["fundamental", "project_dig", "behavioral"],
                     "coding": ["algorithm"],
                     "whiteboard": ["system_design"]}

_ALLOWED_RESUME_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}


def _q_to_dict(q: Question, tags: list[str]) -> dict:
    return {"id": q.id, "title": q.title, "content": q.content,
            "type": q.question_type, "difficulty": q.difficulty,
            "test_cases": q.test_cases or [], "tags": tags,
            "reference_answer": q.reference_answer or ""}


@router.get("/positions")
def list_positions(db: Session = Depends(get_db)):
    rows = db.query(Position).filter(Position.status == 1).all()
    return [{"id": p.id, "name": p.name, "code": p.code, "description": p.description}
            for p in rows]


@router.get("/questions/public")
def public_questions(position_code: str = "backend", difficulty: int = 2,
                     voice: int = 6, coding: int = 2, whiteboard: int = 1,
                     tags: str = Query(default=""),
                     db: Session = Depends(get_db)):
    """游客模式出题：按环节抽取题目（不落库、不消耗配额）。
    若传入简历技术栈 tags，语音题优先匹配相关标签，其余环节保证题型数量。"""
    result = {"voice": [], "coding": [], "whiteboard": []}
    resume_tags = set((t or "").strip() for t in tags.split(",") if t and t.strip())
    for section, count in [("voice", voice), ("coding", coding), ("whiteboard", whiteboard)]:
        if count <= 0:
            continue
        types = _SECTION_TYPE_MAP[section]
        base_query = (db.query(Question)
                      .filter(Question.status == 1,
                              Question.question_type.in_(types),
                              Question.difficulty <= difficulty))
        rows = base_query.order_by(Question.difficulty.desc()).all()

        # 若传入简历标签，优先挑选命中标签的题目；不足再兜底
        if resume_tags and section == "voice":
            tagged_ids = (db.query(QuestionTag.question_id)
                          .filter(QuestionTag.tag_name.in_(list(resume_tags)))
                          .distinct()
                          .subquery())
            tagged = base_query.filter(Question.id.in_(tagged_ids)).order_by(Question.difficulty.desc()).all()
            others = [q for q in rows if q.id not in {x.id for x in tagged}]
            rows = tagged + others

        # 题库不足时允许重复补齐
        picked = rows[:count] if len(rows) >= count else (rows * (count // max(len(rows), 1) + 1))[:count]
        tag_map = {}
        if picked:
            tag_rows = (db.query(QuestionTag)
                        .filter(QuestionTag.question_id.in_([q.id for q in picked])).all())
            for t in tag_rows:
                tag_map.setdefault(t.question_id, []).append(t.tag_name)
        result[section] = [_q_to_dict(q, tag_map.get(q.id, [])) for q in picked]
    if not any(result.values()):
        raise HTTPException(500, "题库为空，请先执行初始化脚本导入种子数据")
    return result


@router.post("/resume/parse", response_model=ResumeParseOut)
async def public_parse_resume(file: UploadFile = File(...)):
    """公开简历解析接口：不落库，供游客模式上传简历使用。"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext or ext not in _ALLOWED_RESUME_EXTS:
        raise HTTPException(400, f"仅支持 {', '.join(sorted(_ALLOWED_RESUME_EXTS))} 格式简历")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "简历大小不能超过 10MB")
    parsed = parse_resume(data, file.filename)
    return ResumeParseOut(**parsed)


@router.post("/interview/mock-reply")
def public_mock_reply(data: MockReplyIn):
    return mock_reply(data.question, data.answer, data.followup_no, history=data.history)


@router.post("/interview/run-code")
def public_run_code(data: RunCodeIn):
    return judge_code(data.question, data.code)


@router.post("/interview/evaluate")
def public_evaluate(data: EvaluateIn):
    # 新版：按题分组（题目顺序与 qa_groups.no 一一对应），带完整对话上下文
    if data.qa_groups:
        return evaluate(_build_items_from_qa(data.questions, data.qa_groups),
                        data.coding_pass_rate, data.whiteboard_elements)
    # 旧版兼容：questions + 平铺 answers
    return evaluate_legacy(data.questions, data.answers,
                           data.coding_pass_rate, data.whiteboard_elements)


def _build_items_from_qa(questions: list[dict], qa_groups: list[dict]) -> list[dict]:
    """把游客模式的题目快照与按题分组回答组装成评分输入。"""
    items = []
    for grp in qa_groups:
        try:
            no = int(grp.get("no", len(items) + 1))
        except Exception:
            no = len(items) + 1
        q = questions[no - 1] if 0 < no <= len(questions) else {}
        items.append({
            "no": no,
            "type": q.get("type") or q.get("question_type") or "fundamental",
            "title": q.get("title") or f"题目{no}",
            "content": q.get("content") or "",
            "difficulty": q.get("difficulty", 1),
            "tags": q.get("tags") or [],
            "reference_answer": q.get("reference_answer") or "",
            "turns": grp.get("turns") or [],
            "coding": grp.get("coding"),
            "whiteboard": grp.get("whiteboard"),
        })
    return items
