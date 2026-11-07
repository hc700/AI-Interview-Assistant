import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 环境变量（固定指向 backend/.env，与启动目录无关）
load_dotenv(os.path.join(BASE_DIR, ".env"))

# MySQL 连接串，可通过环境变量 DB_URL 覆盖
DB_URL = os.getenv(
    "DB_URL",
    "mysql+pymysql://root:123456@localhost:3306/ai_interview?charset=utf8mb4",
)

SECRET_KEY = os.getenv("SECRET_KEY", "ai-interview-dev-secret-2026")
TOKEN_EXPIRE_HOURS = 72

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

# 免费用户每月面试场次上限
FREE_MONTHLY_QUOTA = 3

# DeepSeek / OpenAI-compatible API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
