# 🏭 Factory Environment Alarm V2

> **Linux + PostgreSQL migration version**  
> Arduino 센서 기반 공장 환경 이상 감지 시스템을 **Windows + SQLite 기반 V1**에서 **WSL2 Ubuntu + PostgreSQL 기반 V2**로 이식한 학습 프로젝트입니다.

V1의 핵심 흐름은 그대로 유지했습니다.

```text
센서 측정
   ↓
Arduino 현장 알람
   ↓
작업자 ACK / 재알람
   ↓
Python Middleware
   ↓
PostgreSQL
   ↓
Streamlit Dashboard
```

V1 코드는 `main` 브랜치에 그대로 보존하고, 이 브랜치(`v2-postgresql-linux`)는 **V2에 필요한 코드와 설정만 남기는 방향**으로 정리했습니다.

---

## ✨ V2에서 바뀐 것

| 구분 | Version 1 | Version 2 |
|---|---|---|
| 실행 환경 | Windows | WSL2 Ubuntu / Linux |
| Database | SQLite | PostgreSQL |
| Python DB Driver | `sqlite3` | `psycopg` |
| DB 접근 방식 | `.db` 파일 직접 열기 | PostgreSQL Server 접속 |
| DB 설정 | `DB_PATH` | `.env`의 `DATABASE_URL` |
| SQL Placeholder | `?` | `%s` |
| Primary Key | `AUTOINCREMENT` | `BIGSERIAL` |
| 시간 타입 | `TEXT` | `TIMESTAMPTZ` |
| 시간 생성 | Python `datetime.now()` | PostgreSQL `DEFAULT NOW()` |
| Alarm 값 | `INTEGER` 0/1 | `BOOLEAN` |
| Serial Port | `COM8` | `/dev/ttyACM0` 기본값 |
| Dashboard | Streamlit | Streamlit 유지 |
| Arduino Protocol | `DATA`, `EVENT` | 동일 |

핵심은 **프로그램 역할은 유지하면서 DB와 실행 환경만 교체한 것**입니다.

---

## 🧩 V2 Architecture

```text
DHT11 / Light Sensor
        ↓
Arduino UNO R4 Minima
        ↓
LED · Buzzer · Switch
        ↓
USB Serial
        ↓
Linux Serial Device
(/dev/ttyACM0)
        ↓
Python Middleware
        ↓
       db.py
        ↓
      psycopg
        ↓
    PostgreSQL
        ↓
Streamlit Dashboard
```

### 연결 역할

```text
pyserial
= Python ↔ Arduino

psycopg
= Python ↔ PostgreSQL
```

---

# 🐍 Python 파일별 V1 → V2 비교

## `db.py` — V2에서 새로 추가

| V1 | V2 | 이유 |
|---|---|---|
| 별도 연결 모듈 없음 | `db.py` 추가 | DB 연결을 한 곳에서 관리 |
| 각 파일에서 `sqlite3.connect()` | `get_connection()` 사용 | 공통 연결 방식 사용 |
| `DB_PATH` 사용 | `DATABASE_URL` 사용 | 파일 경로가 아니라 DB Server 접속 |
| 접속정보 코드 내부 관리 | `.env` 사용 | 코드와 환경설정 분리 |

```text
.env
 ↓
db.py
 ↓
get_connection()
 ↓
psycopg
 ↓
PostgreSQL
```

---

## `init_db.py` — DB 파일 생성 → PostgreSQL Schema 초기화

| V1 | V2 | 이유 |
|---|---|---|
| `sqlite3` 사용 | `get_connection()` 사용 | PostgreSQL 연결 |
| `data/` 폴더 생성 | 필요 없음 | V2는 `.db` 파일을 만들지 않음 |
| `factory_alarm.db` 생성 | PostgreSQL DB에 Table 생성 | 파일 DB → Server DB |
| `executescript()` | `cursor.execute()` | PostgreSQL 방식으로 Schema 실행 |

```text
V1
schema.sql → init_db.py → factory_alarm.db

V2
schema.sql → init_db.py → db.py → PostgreSQL
```

---

## `middleware.py` — SQLite 저장 → PostgreSQL 저장

Middleware의 역할 자체는 동일합니다.

```text
Arduino Serial 수신
        ↓
DATA / EVENT 파싱
        ↓
DB 저장
```

| V1 | V2 | 이유 |
|---|---|---|
| `sqlite3.connect(DB_PATH)` | `get_connection()` | PostgreSQL 연결 |
| `VALUES (?, ...)` | `VALUES (%s, ...)` | psycopg Placeholder |
| Alarm 0/1 그대로 저장 | `bool(...)` 변환 | PostgreSQL `BOOLEAN` 대응 |
| Python에서 측정시각 생성 | DB `NOW()` 사용 | 시간 기록을 DB에 위임 |
| `PORT = "COM8"` | `SERIAL_PORT` / `/dev/ttyACM0` | Linux Serial 대응 |
| Port가 코드에 고정 | 환경변수로 변경 가능 | 실행환경별 설정 분리 |

Arduino가 보내는 Protocol은 그대로 사용합니다.

```text
DATA,temperature,humidity,light,temp_alarm,hum_alarm,light_alarm,acknowledged,alert_active
```

```text
EVENT,ALARM_START
EVENT,ACK
EVENT,RE_ALERT
EVENT,NORMAL
```

---

## `dashboard.py` — SQLite 직접 조회 → PostgreSQL 조회

| V1 | V2 | 이유 |
|---|---|---|
| SQLite 파일 직접 조회 | PostgreSQL 조회 | 저장소 변경 |
| `DB_PATH` 사용 | `db.py` 사용 | DB 연결 공통화 |
| `pd.read_sql_query()` + SQLite Connection | Cursor 조회 → DataFrame 변환 | psycopg 결과 처리 |
| SQL `?` | SQL `%s` | Driver 차이 |
| 시간 문자열 비교 | Time Zone 포함 `datetime` 전달 | `TIMESTAMPTZ` 대응 |

Dashboard의 역할은 그대로입니다.

- 현재 온도 / 습도 / 조도 표시
- 정상 / 이상 상태 표시
- Threshold 기준선
- Trend Chart
- Alarm Event History
- 2초 주기 자동 갱신

---

## 🗄️ Schema 차이

### `sensor_data`

| SQLite V1 | PostgreSQL V2 |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` |
| `measured_at TEXT` | `TIMESTAMPTZ DEFAULT NOW()` |
| Alarm 관련 `INTEGER` | Alarm 관련 `BOOLEAN` |

### `alarm_event`

| SQLite V1 | PostgreSQL V2 |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` |
| `event_at TEXT` | `TIMESTAMPTZ DEFAULT NOW()` |

---

## 📁 V2 Project Structure

```text
Factory-Environment-Alarm-260903/
│
├── arduino/
│   └── factory_alarm/
│       └── factory_alarm.ino
│
├── src/
│   └── factory_environment_alarm/
│       ├── __init__.py
│       ├── db.py
│       ├── init_db.py
│       ├── middleware.py
│       └── dashboard.py
│
├── .env.example
├── .gitignore
├── .python-version
├── schema.sql
├── pyproject.toml
├── uv.lock
└── README.md
```

### V2에서 제거한 V1 전용 요소

- `data/factory_alarm.db` 기반 구조
- SQLite DB 경로 관리
- `.db` 파일용 Git ignore 규칙
- V1 SQLite 구조를 그린 기존 Architecture 이미지
- 기본 생성 예제용 Python entrypoint

V2의 실제 센서 데이터는 **프로젝트 폴더 안 파일이 아니라 PostgreSQL Server에 저장**됩니다.

---

## 🔐 Environment Variables

실제 `.env`는 GitHub에 올리지 않습니다.

먼저 예제 파일을 복사합니다.

```bash
cp .env.example .env
```

`.env` 예시:

```env
DATABASE_URL=postgresql://factory_user:your_password@localhost:5432/factory_alarm
SERIAL_PORT=/dev/ttyACM0
SERIAL_BAUDRATE=115200
```

`DATABASE_URL`은 파일 위치가 아니라 다음 정보를 한 줄로 표현한 **PostgreSQL 접속 주소**입니다.

```text
postgresql://사용자:비밀번호@서버:포트/데이터베이스
```

---

## 🚀 Run

### 1. Dependency 설치

```bash
uv sync
```

### 2. PostgreSQL Schema 초기화

```bash
python src/factory_environment_alarm/init_db.py
```

### 3. Dashboard 실행

```bash
python -m streamlit run src/factory_environment_alarm/dashboard.py
```

### 4. Middleware 실행

Arduino가 Linux Serial Device로 연결된 뒤 실행합니다.

```bash
python src/factory_environment_alarm/middleware.py
```

---

## 🚨 Alarm Threshold

| 항목 | 정상 범위 | 이상 조건 |
|---|---:|---:|
| 🌡️ 온도 | 18 ~ 28 ℃ | 18 ℃ 미만 또는 28 ℃ 초과 |
| 💧 습도 | 40 ~ 70 % | 40 % 미만 또는 70 % 초과 |
| ☀️ 조도 | 300 미만 | 300 이상 |

현재 회로에서는 **조도 센서값이 커질수록 어두운 상태**로 판단합니다.

---

## ✅ Migration Status

- [x] WSL2 Ubuntu 환경 구성
- [x] PostgreSQL 설치
- [x] `factory_alarm` Database / `factory_user` 구성
- [x] `psycopg` 연결 확인
- [x] PostgreSQL Schema 변환
- [x] `db.py` 공통 연결 구조 추가
- [x] `init_db.py` 변환
- [x] `middleware.py` 변환
- [x] `dashboard.py` 변환
- [x] Streamlit → PostgreSQL 조회 확인
- [ ] Arduino USB → WSL2 연결
- [ ] Linux Serial 실수신 테스트
- [ ] Arduino → PostgreSQL → Streamlit End-to-End 테스트
- [ ] V2 별도 Public Repository로 최종 분리

---

## 💡 핵심 학습 포인트

> **SQLite는 DB 파일을 직접 열고, PostgreSQL은 DB Server에 접속한다.**

```text
SQLite
Python → factory_alarm.db

PostgreSQL
Python → psycopg → PostgreSQL Server → factory_alarm Database
```

그래서 V1의 `DB_PATH`는 사라지고, V2에서는 `DATABASE_URL`을 사용합니다.

---

## 👩‍💻 Author

**chodaseul**  
AI Smart Manufacturing Training Project · 2026
