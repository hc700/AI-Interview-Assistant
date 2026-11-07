from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import UPLOAD_DIR
from .database import Base, SessionLocal, engine
from .routers import auth, billing, questions, sessions, users


def create_app() -> FastAPI:
    app = FastAPI(title="AI 模拟面试助手", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(questions.router)
    app.include_router(sessions.router)
    app.include_router(billing.router)

    import os
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    @app.on_event("startup")
    def on_startup():
        # 自动建表 + 种子数据（数据库需已存在，首次请先执行 python -m app.init_db）
        try:
            Base.metadata.create_all(bind=engine)
            from .seed import seed_all
            db = SessionLocal()
            try:
                seed_all(db)
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            print(f"[startup] 数据库初始化跳过：{e}")

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "ai-interview"}

    return app


app = create_app()
