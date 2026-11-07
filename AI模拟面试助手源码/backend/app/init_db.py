"""初始化数据库：创建库 + 建表 + 种子数据。

用法：
    python -m app.init_db
可先通过环境变量覆盖连接：DB_URL=mysql+pymysql://user:pass@host:3306/ai_interview
"""
from .database import Base, SessionLocal, engine
from .seed import seed_all


def main():
    # 1. 创建数据库（若不存在）
    u = engine.url
    if u.drivername.startswith("mysql"):
        import pymysql
        conn = pymysql.connect(host=u.host, port=u.port or 3306,
                               user=u.username, password=u.password or "")
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{u.database}` "
                    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            print(f"[init_db] 数据库 `{u.database}` 已就绪")
        finally:
            conn.close()

    # 2. 建表
    Base.metadata.create_all(bind=engine)
    print("[init_db] 数据表已创建")

    # 3. 种子数据
    db = SessionLocal()
    try:
        seed_all(db)
        print("[init_db] 种子数据已导入（岗位 / 套餐 / 题库 / 演示账号 demo@interview.cn）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
