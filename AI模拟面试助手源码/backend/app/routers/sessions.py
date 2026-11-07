"""面试会话：创建（出题+扣配额）→ 开始 → 问答/编程/白板 → 结束评分 → 报告。"""
import json
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai_engine import evaluate, evaluate_legacy, judge_code, mock_reply
from ..database import get_db
from ..deps import get_current_user, get_or_create_quota, is_member
from ..models import (
    CodingSubmission, DimensionEvaluation, InterviewDialogue, InterviewSession,
    Position, Question, QuestionEvaluation, QuestionTag, Resume, SessionEvaluation,
    SessionQuestion, SessionSection, User, WhiteboardSnapshot,
)
from ..schemas import (
    CodingSubmitIn, DialogueIn, SessionCreateIn, WhiteboardSnapshotIn,
)
from ..seed import snapshot_of

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_SECTION_TYPE_MAP = {"voice": ["fundamental", "project_dig", "behavioral"],
                     "coding": ["algorithm"],
                     "whiteboard": ["system_design"]}


def _session_detail(db: Session, s: InterviewSession) -> dict:
    sections = (db.query(SessionSection)
                .filter(SessionSection.session_id == s.id)
                .order_by(SessionSection.sequence_no).all())
    questions = (db.query(SessionQuestion)
                 .filter(SessionQuestion.session_id == s.id)
                 .order_by(SessionQuestion.sequence_no).all())
    pos = db.get(Position, s.position_id)
    section_type_by_id = {sec.id: sec.section_type for sec in sections}
    return {
        "id": s.id, "status": s.status,
        "position": {"id": pos.id, "name": pos.name} if pos else None,
        "difficulty": s.difficulty, "duration_min": s.duration_min,
        "question_mix": s.question_mix, "resume_id": s.resume_id,
        "overall_score": float(s.overall_score) if s.overall_score is not None else None,
        "overall_comment": s.overall_comment,
        "started_at": s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else None,
        "ended_at": s.ended_at.strftime("%Y-%m-%d %H:%M") if s.ended_at else None,
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M"),
        "is_member": is_member(db, s.user_id),
        "sections": [{"id": sec.id, "section_type": sec.section_type,
                      "sequence_no": sec.sequence_no, "status": sec.status}
                     for sec in sections],
        "questions": [{"id": q.id, "source": q.source,
                       "section_type": section_type_by_id.get(q.section_id, "voice"),
                       "sequence_no": q.sequence_no,
                       "snapshot": json.loads(q.question_snapshot)}
                      for q in questions],
    }


def _pick_questions(db: Session, types: list[str], count: int, difficulty: int):
    rows = (db.query(Question)
            .filter(Question.status == 1,
                    Question.question_type.in_(types),
                    Question.difficulty <= difficulty)
            .order_by(Question.difficulty.desc()).all())
    if not rows:
        return []
    picked = rows[:count] if len(rows) >= count else (rows * (count // len(rows) + 1))[:count]
    tag_map = {}
    tag_rows = (db.query(QuestionTag)
                .filter(QuestionTag.question_id.in_([q.id for q in picked])).all())
    for t in tag_rows:
        tag_map.setdefault(t.question_id, []).append(t.tag_name)
    return [(q, tag_map.get(q.id, [])) for q in picked]


@router.post("")
def create_session(data: SessionCreateIn,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    # 配额校验（会员不限次）
    quota = get_or_create_quota(db, user.id)
    if not is_member(db, user.id) and quota.used_count >= quota.quota_limit:
        raise HTTPException(403, f"本月免费额度已用完（{quota.used_count}/{quota.quota_limit}），开通会员即可不限次练习")

    if not db.get(Position, data.position_id):
        raise HTTPException(400, "岗位不存在")
    if data.resume_id:
        resume = db.query(Resume).filter(Resume.id == data.resume_id,
                                         Resume.user_id == user.id,
                                         Resume.is_deleted == 0).first()
        if not resume:
            raise HTTPException(400, "简历不存在")

    mix = {"voice": max(0, int(data.question_mix.get("voice", 6))),
           "coding": max(0, int(data.question_mix.get("coding", 2))),
           "whiteboard": max(0, int(data.question_mix.get("whiteboard", 1)))}
    if sum(mix.values()) == 0:
        raise HTTPException(400, "至少选择一道题目")

    s = InterviewSession(user_id=user.id, position_id=data.position_id,
                         resume_id=data.resume_id, difficulty=data.difficulty,
                         duration_min=data.duration_min, question_mix=mix,
                         status="configured")
    db.add(s)
    db.flush()

    seq = 0
    for section_type in ["voice", "coding", "whiteboard"]:
        count = mix[section_type]
        if count <= 0:
            continue
        section = SessionSection(session_id=s.id, section_type=section_type,
                                 sequence_no=len(db.query(SessionSection)
                                                 .filter(SessionSection.session_id == s.id)
                                                 .all()) + 1,
                                 status="pending")
        db.add(section)
        db.flush()
        for q, tags in _pick_questions(db, _SECTION_TYPE_MAP[section_type], count,
                                       data.difficulty):
            seq += 1
            db.add(SessionQuestion(session_id=s.id, section_id=section.id,
                                   question_id=q.id, question_snapshot=snapshot_of(q, tags),
                                   source="builtin", sequence_no=seq))

        # 简历定制题：附加到语音环节（会员完整支持 / 免费基础支持）
        if section_type == "voice" and data.resume_id:
            resume = db.get(Resume, data.resume_id)
            if resume and resume.tech_tags:
                tags = resume.tech_tags
                custom = (f"你的简历中提到了「{tags[0]}」相关技术。请结合你的项目经历，"
                          f"讲讲你是如何在实际业务中使用它的，遇到过什么问题？")
                seq += 1
                db.add(SessionQuestion(
                    session_id=s.id, section_id=section.id, question_id=None,
                    question_snapshot=json.dumps({
                        "id": None, "title": f"简历深挖 · {tags[0]}",
                        "content": custom, "type": "project_dig",
                        "difficulty": data.difficulty, "test_cases": [], "tags": ["简历定制"],
                    }, ensure_ascii=False),
                    source="resume_custom", sequence_no=seq))

    quota.used_count += 1
    db.commit()
    db.refresh(s)
    return _session_detail(db, s)


@router.get("")
def list_sessions(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    rows = (db.query(InterviewSession)
            .filter(InterviewSession.user_id == user.id)
            .order_by(InterviewSession.created_at.desc()).all())
    result = []
    for s in rows:
        pos = db.get(Position, s.position_id)
        result.append({
            "id": s.id, "status": s.status, "created_at": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "position_name": pos.name if pos else "-",
            "difficulty": s.difficulty,
            "score": float(s.overall_score) if s.overall_score is not None else None,
        })
    return result


@router.get("/{session_id}")
def get_session(session_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")
    return _session_detail(db, s)


@router.post("/{session_id}/start")
def start_session(session_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")
    if s.status == "completed":
        raise HTTPException(400, "该面试已结束")
    if s.status == "configured":
        s.status = "in_progress"
        s.started_at = datetime.now()
        first = (db.query(SessionSection)
                 .filter(SessionSection.session_id == s.id)
                 .order_by(SessionSection.sequence_no).first())
        if first:
            first.status = "in_progress"
            first.started_at = datetime.now()
        db.commit()
    return _session_detail(db, s)


@router.post("/{session_id}/dialogue")
def dialogue(session_id: int, data: DialogueIn,
             user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")

    question_snapshot = None
    if data.question_id:
        sq = db.query(SessionQuestion).filter(
            SessionQuestion.id == data.question_id,
            SessionQuestion.session_id == s.id).first()
        if sq:
            question_snapshot = json.loads(sq.question_snapshot)

    # 先保存考生回答
    db.add(InterviewDialogue(session_id=s.id, section_id=data.section_id,
                             speaker="candidate", content=data.content))
    db.commit()

    # 组装本题历史上下文（同一 section 下最近的 candidate/interviewer 交替记录）
    history_rows = (db.query(InterviewDialogue)
                    .filter(InterviewDialogue.session_id == s.id,
                            InterviewDialogue.section_id == data.section_id)
                    .order_by(InterviewDialogue.id.asc())
                    .all())
    history = []
    last_ai = None
    for row in history_rows:
        if row.speaker == "interviewer":
            last_ai = row.content
        elif row.speaker == "candidate" and last_ai is not None:
            history.append({"ai": last_ai, "user": row.content})
            last_ai = None

    reply = mock_reply(question_snapshot or {"title": "", "type": "fundamental"},
                       data.content, data.followup_no, history=history)
    db.add(InterviewDialogue(session_id=s.id, section_id=data.section_id,
                             speaker="interviewer", content=reply["reply"]))
    db.commit()
    return reply


@router.post("/{session_id}/coding/submit")
def coding_submit(session_id: int, data: CodingSubmitIn,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")

    question_snapshot = None
    if data.question_id:
        sq = db.query(SessionQuestion).filter(
            SessionQuestion.id == data.question_id,
            SessionQuestion.session_id == s.id).first()
        if sq:
            question_snapshot = json.loads(sq.question_snapshot)

    result = judge_code(question_snapshot or {"title": "", "test_cases": []}, data.code)
    submission = CodingSubmission(
        session_id=s.id, section_id=data.section_id,
        session_question_id=data.question_id, language=data.language,
        code=data.code, run_status=result["run_status"], run_result=result)
    db.add(submission)
    db.commit()
    return result


@router.post("/{session_id}/whiteboard/snapshot")
def whiteboard_snapshot(session_id: int, data: WhiteboardSnapshotIn,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")
    db.add(WhiteboardSnapshot(session_id=s.id, section_id=data.section_id,
                              content=data.content))
    db.commit()
    return {"ok": True, "saved_at": datetime.now().strftime("%H:%M:%S")}


@router.post("/{session_id}/finish")
def finish_session(session_id: int, payload: dict,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """结束面试并生成评分。payload 可携带 guest 模式补充数据：
    {answers: [...], coding_pass_rate: 0~1, whiteboard_elements: n}"""
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")
    if s.status == "completed":
        return get_report(session_id, user, db)

    questions = (db.query(SessionQuestion)
                 .filter(SessionQuestion.session_id == s.id)
                 .order_by(SessionQuestion.sequence_no).all())

    # 汇总数据：优先用 payload，缺失时回退到库内记录
    answers = payload.get("answers") or []
    if not answers:
        dlg = (db.query(InterviewDialogue)
               .filter(InterviewDialogue.session_id == s.id,
                       InterviewDialogue.speaker == "candidate")
               .order_by(InterviewDialogue.created_at).all())
        answers = [d.content for d in dlg]

    coding_pass_rate = payload.get("coding_pass_rate")
    if coding_pass_rate is None:
        subs = (db.query(CodingSubmission)
                .filter(CodingSubmission.session_id == s.id)
                .order_by(CodingSubmission.submitted_at.desc()).all())
        if subs:
            best = subs[0].run_result or {}
            coding_pass_rate = best.get("passed", 0) / max(best.get("total", 1), 1)
        else:
            coding_pass_rate = 0.0

    wb_elements = payload.get("whiteboard_elements")
    if wb_elements is None:
        snap = (db.query(WhiteboardSnapshot)
                .filter(WhiteboardSnapshot.session_id == s.id)
                .order_by(WhiteboardSnapshot.created_at.desc()).first())
        wb_elements = len((snap.content or {}).get("nodes", [])) if snap else 0

    q_dicts = [json.loads(q.question_snapshot) for q in questions]

    # ---------- 组装按题评分的输入 ----------
    # 新版前端提交 qa_groups：每题一组（含多轮对话、代码、白板），顺序与 no 一一对应
    qa_groups = payload.get("qa_groups") or []
    if qa_groups:
        grp_by_no = {}
        for grp in qa_groups:
            try:
                grp_by_no[int(grp.get("no"))] = grp
            except Exception:
                continue
        items = []
        for i, sq in enumerate(questions):
            no = i + 1
            grp = grp_by_no.get(no) or {}
            snap = json.loads(sq.question_snapshot)
            # 从题库补齐参考答案要点（评分依据），简历定制题则用题目自带信息
            q_row = db.get(Question, sq.question_id) if sq.question_id else None
            ref = snap.get("reference_answer") or (q_row.reference_answer if q_row else "") or ""
            items.append({
                "no": no,
                "type": snap.get("type") or sq.section_type or "fundamental",
                "title": snap.get("title") or f"题目{no}",
                "content": snap.get("content") or "",
                "difficulty": snap.get("difficulty", 1),
                "tags": snap.get("tags") or [],
                "reference_answer": ref,
                "turns": grp.get("turns") or [],
                "coding": grp.get("coding"),
                "whiteboard": grp.get("whiteboard"),
            })
        result = evaluate(items, float(coding_pass_rate), int(wb_elements))
    else:
        # 旧版兼容：未带分组数据时，用平铺回答按题目下标粗略对应
        result = evaluate_legacy(q_dicts, answers, float(coding_pass_rate), int(wb_elements))

    s.status = "completed"
    s.ended_at = datetime.now()
    s.overall_score = result["total_score"]
    s.overall_comment = result["overall_comment"][:490]
    for sec in db.query(SessionSection).filter(SessionSection.session_id == s.id).all():
        sec.status = "completed"
        if not sec.ended_at:
            sec.ended_at = datetime.now()

    db.add(SessionEvaluation(session_id=s.id, total_score=result["total_score"],
                             overall_comment=result["overall_comment"][:490]))

    if not db.query(SessionEvaluation).filter(
            SessionEvaluation.session_id == s.id).count():
        pass  # 上面已 add，避免重复

    for d in result["dimensions"]:
        db.add(DimensionEvaluation(session_id=s.id, dimension=d["dimension"],
                                   score=d["score"], feedback=d["feedback"]))
    qe_by_no = {i + 1: qe for i, qe in enumerate(result["question_evaluations"])}
    for i, q in enumerate(questions):
        qe = qe_by_no.get(i + 1)
        if not qe:
            continue
        db.add(QuestionEvaluation(session_id=s.id, session_question_id=q.id,
                                  score=qe["score"], feedback=qe["feedback"],
                                  reference_compare=qe.get("suggestion") or None))

    db.commit()
    db.refresh(s)
    return get_report(session_id, user, db)


def get_report(session_id: int, user: User, db: Session) -> dict:
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                          InterviewSession.user_id == user.id).first()
    if not s:
        raise HTTPException(404, "面试会话不存在")
    member = is_member(db, user.id)
    detail = _session_detail(db, s)

    dims, per_q = [], []
    if member:
        dim_rows = db.query(DimensionEvaluation).filter(
            DimensionEvaluation.session_id == s.id).all()
        from ..ai_engine import _DIM_NAMES
        dims = [{"dimension": d.dimension, "name": _DIM_NAMES.get(d.dimension, d.dimension),
                 "score": float(d.score), "feedback": d.feedback} for d in dim_rows]
        qe_rows = db.query(QuestionEvaluation).filter(
            QuestionEvaluation.session_id == s.id).all()
        qe_map = {qe.session_question_id: qe for qe in qe_rows}
        per_q = []
        for q in detail["questions"]:
            qe = qe_map.get(q["id"])
            if qe:
                per_q.append({"title": q["snapshot"]["title"], "type": q["snapshot"]["type"],
                              "score": float(qe.score), "feedback": qe.feedback,
                              "suggestion": qe.reference_compare or ""})

    return {
        "session": detail,
        "evaluation": {"total_score": float(s.overall_score or 0),
                       "overall_comment": s.overall_comment or ""},
        "dimensions": dims,
        "question_evaluations": per_q,
        "is_member": member,
    }


@router.get("/{session_id}/report")
def report(session_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return get_report(session_id, user, db)
