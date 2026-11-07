import os
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR
from ..database import get_db
from ..deps import get_current_user, get_or_create_quota, is_member
from ..models import InterviewSession, Resume, User
from ..resume_parser import parse_resume
from ..schemas import ResumeOut

_ALLOWED_RESUME_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}

router = APIRouter(prefix="/api/users/me", tags=["users"])


@router.get("/quota")
def quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = get_or_create_quota(db, user.id)
    return {"used": q.used_count, "limit": q.quota_limit,
            "is_member": is_member(db, user.id)}


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user.id,
                InterviewSession.status == "completed")
        .order_by(InterviewSession.created_at.asc())
        .all())
    scores = [float(s.overall_score) for s in sessions if s.overall_score is not None]
    q = get_or_create_quota(db, user.id)
    return {
        "total_sessions": len(sessions),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "quota": {"used": q.used_count, "limit": q.quota_limit},
        "is_member": is_member(db, user.id),
        "trend": [{"session_id": s.id, "date": s.created_at.strftime("%Y-%m-%d"),
                   "score": float(s.overall_score)} for s in sessions if s.overall_score],
    }


@router.get("/resumes", response_model=list[ResumeOut])
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Resume)
            .filter(Resume.user_id == user.id, Resume.is_deleted == 0)
            .order_by(Resume.uploaded_at.desc()).all())
    return [ResumeOut(id=r.id, file_name=r.file_name, summary=r.parsed_content.get("summary") if r.parsed_content else None,
                      tech_tags=r.tech_tags,
                      uploaded_at=r.uploaded_at.strftime("%Y-%m-%d %H:%M")) for r in rows]


@router.post("/resumes", response_model=ResumeOut)
async def upload_resume(file: UploadFile,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext or ext not in _ALLOWED_RESUME_EXTS:
        raise HTTPException(400, f"仅支持 {', '.join(sorted(_ALLOWED_RESUME_EXTS))} 格式简历")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "简历大小不能超过 10MB")

    # 真实解析简历文本与技术栈
    parsed_info = parse_resume(data, file.filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{user.id}_{int(time.time())}_{os.path.basename(file.filename)}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(data)

    parsed = {
        "summary": parsed_info.get("summary", ""),
        "word_count": parsed_info.get("word_count", 0),
        "suggestions": ["建议深挖「项目难点」与「线上故障处理」",
                        "技术栈关键词将用于定制追问"],
    }
    tech_tags = parsed_info.get("tech_tags") or []
    resume = Resume(user_id=user.id, file_name=file.filename,
                    file_url=f"/uploads/{safe_name}",
                    parsed_content=parsed, tech_tags=tech_tags)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return ResumeOut(id=resume.id, file_name=resume.file_name, summary=parsed["summary"],
                     tech_tags=tech_tags,
                     uploaded_at=resume.uploaded_at.strftime("%Y-%m-%d %H:%M"))


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")
    resume.is_deleted = 1  # 软删除，满足隐私合规
    db.commit()
    return {"ok": True}
