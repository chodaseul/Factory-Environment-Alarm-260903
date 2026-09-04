import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL 환경변수가 설정되지 않았습니다."
        )

    return psycopg.connect(DATABASE_URL)
