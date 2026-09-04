from pathlib import Path

from factory_environment_alarm.db import get_connection


# =====================================================
# 경로 설정
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

SCHEMA_PATH = BASE_DIR / "schema.sql"


# =====================================================
# PostgreSQL DB 초기화
# =====================================================

def init_db():
    schema = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    statements = [
        statement.strip()
        for statement in schema.split(";")
        if statement.strip()
    ]

    with get_connection() as conn:
        with conn.cursor() as cursor:

            for statement in statements:
                cursor.execute(statement)

    print("PostgreSQL DB 초기화 완료!")
    print("Database : factory_alarm")


# =====================================================
# 직접 실행
# =====================================================

if __name__ == "__main__":
    init_db()
