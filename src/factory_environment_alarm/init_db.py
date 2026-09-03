import sqlite3
from pathlib import Path


# =====================================================
# 경로 설정
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "factory_alarm.db"

SCHEMA_PATH = BASE_DIR / "schema.sql"


# =====================================================
# DB 초기화
# =====================================================

def init_db():
    # data 폴더가 없으면 생성
    DB_DIR.mkdir(exist_ok=True)

    # schema.sql 읽기
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()

    # DB 연결
    conn = sqlite3.connect(DB_PATH)

    try:
        # schema.sql 안의 여러 SQL문 한 번에 실행
        conn.executescript(schema)

        conn.commit()

        print("DB 초기화 완료!")
        print(f"DB 위치 : {DB_PATH}")

    finally:
        conn.close()


# =====================================================
# 직접 실행했을 때만 실행
# =====================================================

if __name__ == "__main__":
    init_db()