# 🏭 Factory Environment Alarm V2

Arduino 센서 기반 공장 환경 이상 감지 시스템을 **Windows + SQLite 기반 V1에서 Linux(WSL2) + PostgreSQL 기반 V2로 이식**하는 학습 프로젝트입니다.

V1의 핵심 흐름인 **센서 측정 → 현장 알람 → 작업자 ACK → 재알람 → 이력 저장 → Dashboard 모니터링**은 유지하고, 운영 환경과 데이터베이스 계층을 변경했습니다.

> V1 기준 코드는 `main` 브랜치에 보존합니다.  
> 이 브랜치(`v2-postgresql-linux`)는 V1을 PostgreSQL/Linux 환경으로 옮기면서 차이점을 학습하기 위한 V2 작업 브랜치입니다.

---

## 🎯 V2 Migration Goal

```text
V1
Windows
  ↓
Arduino COM Port
  ↓
Python Middleware
  ↓
SQLite (factory_alarm.db)
  ↓
Streamlit Dashboard

            ↓ Migration

V2
Linux / WSL2
  ↓
Arduino Linux Serial (/dev/ttyACM0 예정)
  ↓
Python Middleware
  ↓
db.py / psycopg
  ↓
PostgreSQL
  ↓
Streamlit Dashboard
```

이번 V2의 핵심은 프로그램을 새로 만드는 것이 아니라, **기존 애플리케이션 구조를 유지한 채 DB와 실행 환경을 교체하는 것**입니다.

---

## 🔄 Version 1 vs Version 2

| 항목 | Version 1 | Version 2 | 변경 이유 |
|---|---|---|---|
| OS | Windows | WSL2 Ubuntu / Linux | Linux 환경에서 재구현 및 운영 구조 학습 |
| Database | SQLite | PostgreSQL | 파일형 DB에서 서버형 DB로 확장 |
| Python DB 모듈 | `sqlite3` | `psycopg` | Python에서 PostgreSQL 연결 |
| DB 위치 | `data/factory_alarm.db` | PostgreSQL Server | 로컬 DB 파일 의존 제거 |
| 연결 설정 | `DB_PATH` | `.env`의 `DATABASE_URL` | 코드와 환경설정 분리 |
| SQL Placeholder | `?` | `%s` | DB Driver 차이 |
| ID | `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` | PostgreSQL 자동 증가 방식 사용 |
| 시간 | `TEXT` | `TIMESTAMPTZ` | 실제 날짜/시간 타입 + Time Zone 지원 |
| 측정시각 생성 | Python `datetime.now()` | PostgreSQL `DEFAULT NOW()` | 시간 기록을 DB에 위임 |
| Alarm 상태 | `INTEGER` 0/1 | `BOOLEAN` | 데이터 의미를 명확하게 표현 |
| Serial Port | `COM8` | `/dev/ttyACM0` 기본값 | Windows → Linux 장치 체계 변경 |
| Serial 설정 | 코드에 직접 작성 | 환경변수로 변경 가능 | 실행 환경별 설정 분리 |
| Dashboard | Streamlit | Streamlit | UI 역할은 유지 |
| Arduino Protocol | `DATA`, `EVENT` | 동일 | 기존 센서/알람 흐름 재사용 |

---

# 🐍 Python 파일별 V1 → V2 변경점

## 1. `db.py` — V2에서 새로 추가

| Version 1 | Version 2 | 의미 |
|---|---|---|
| 별도 DB 연결 모듈 없음 | `db.py` 추가 | DB 연결 로직을 한 곳에서 관리 |
| 각 Python 파일이 `sqlite3.connect(DB_PATH)` 실행 | `get_connection()` 사용 | Middleware / Dashboard / Init에서 동일한 연결 방식 사용 |
| DB 파일 경로 사용 | `DATABASE_URL` 사용 | PostgreSQL Server 접속 정보 사용 |
| 환경설정 분리 없음 | `python-dotenv`로 `.env` 로드 | 접속정보를 소스코드 밖으로 분리 |

핵심 구조:

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

`psycopg`는 **Python과 PostgreSQL을 연결하는 PostgreSQL Driver**입니다.

```python
import psycopg

return psycopg.connect(DATABASE_URL)
```

---

## 2. `init_db.py` — DB 파일 생성 → PostgreSQL Schema 초기화

| Version 1 | Version 2 | 의미 |
|---|---|---|
| `import sqlite3` | `get_connection()` import | DB 연결 방식 변경 |
| `data/` 폴더 생성 | 폴더 생성 없음 | PostgreSQL은 DB 파일을 직접 만들지 않음 |
| `factory_alarm.db` 파일 생성 | 기존 PostgreSQL DB에 접속 | 파일 DB → 서버 DB |
| `sqlite3.connect(DB_PATH)` | `get_connection()` | 공통 DB 연결 모듈 사용 |
| `conn.executescript(schema)` | SQL 문을 분리해 `cursor.execute()` | PostgreSQL에서 Schema 실행 |
| DB 파일 위치 출력 | PostgreSQL DB 이름 출력 | DB 위치 개념 변화 |

V1:

```text
schema.sql
   ↓
init_db.py
   ↓
factory_alarm.db 생성
```

V2:

```text
schema.sql
   ↓
init_db.py
   ↓
db.py / psycopg
   ↓
PostgreSQL의 factory_alarm DB에 Table 생성
```

---

## 3. `middleware.py` — SQLite 저장 → PostgreSQL 저장

Middleware의 본래 역할은 V1과 동일합니다.

```text
Arduino Serial 수신
        ↓
DATA / EVENT 파싱
        ↓
DB 저장
```

DB에 저장하는 방법과 Serial 환경 설정이 변경되었습니다.

| Version 1 | Version 2 | 의미 |
|---|---|---|
| `import sqlite3` | `get_connection()` | PostgreSQL 연결 사용 |
| `DB_PATH` 필요 | DB 파일 경로 없음 | Server DB 사용 |
| `PORT = "COM8"` | `SERIAL_PORT` 또는 `/dev/ttyACM0` | Linux Serial 대응 |
| `BAUDRATE = 115200` | 환경변수로 변경 가능 | 실행환경 설정 분리 |
| `sqlite3.connect(DB_PATH)` | `with get_connection() as conn` | PostgreSQL Connection Context 사용 |
| `VALUES (?, ?, ...)` | `VALUES (%s, %s, ...)` | psycopg Placeholder 사용 |
| Alarm 0/1 그대로 저장 | `bool(...)` 변환 | PostgreSQL BOOLEAN 컬럼 대응 |
| Python이 `measured_at` 생성 | DB `NOW()` 사용 | 측정시간 기록을 DB에 위임 |
| Python이 `event_at` 생성 | DB `NOW()` 사용 | 이벤트 시간도 DB가 기록 |

### Arduino 데이터 처리 자체는 유지

```text
DATA,temperature,humidity,light,temp_alarm,hum_alarm,light_alarm,acknowledged,alert_active
```

즉 Arduino가 보내는 Serial Protocol은 바꾸지 않고 **Middleware의 DB 저장 계층만 교체**했습니다.

```text
V1
pyserial → Python → sqlite3 → SQLite

V2
pyserial → Python → psycopg → PostgreSQL
```

- `pyserial` : Python ↔ Arduino 연결
- `psycopg` : Python ↔ PostgreSQL 연결

---

## 4. `dashboard.py` — SQLite 직접 조회 → PostgreSQL 조회

Dashboard의 센서 카드, Trend Chart, Alarm History 역할은 유지했습니다.

| Version 1 | Version 2 | 의미 |
|---|---|---|
| `import sqlite3` | `get_connection()` | PostgreSQL 연결 사용 |
| `DB_PATH` 직접 사용 | `db.py` 사용 | DB 연결 코드 공통화 |
| `pd.read_sql_query(..., sqlite connection)` | Cursor 조회 후 DataFrame 생성 | PostgreSQL 조회 결과를 pandas로 변환 |
| SQL `?` Placeholder | `%s` Placeholder | psycopg 방식 적용 |
| 조회 시작시간을 문자열로 생성 | Time Zone이 포함된 `datetime` 전달 | `TIMESTAMPTZ`와 맞는 시간 처리 |
| SQLite 파일 조회 | PostgreSQL Table 조회 | 데이터 저장소 교체 |
| 기존 Streamlit UI | 기존 기능 유지 | DB 변경과 UI 역할 분리 |

V2에서는 공통 함수 `query_dataframe()`이 PostgreSQL 결과를 pandas DataFrame으로 변환합니다.

```text
Streamlit
   ↓
dashboard.py
   ↓
query_dataframe()
   ↓
get_connection()
   ↓
psycopg
   ↓
PostgreSQL
```

---

## 🗄️ Schema 변경

### `sensor_data`

| V1 SQLite | V2 PostgreSQL |
|---|---|
| `id INTEGER PRIMARY KEY AUTOINCREMENT` | `id BIGSERIAL PRIMARY KEY` |
| `measured_at TEXT` | `measured_at TIMESTAMPTZ DEFAULT NOW()` |
| `temp_alarm INTEGER` | `temp_alarm BOOLEAN` |
| `hum_alarm INTEGER` | `hum_alarm BOOLEAN` |
| `light_alarm INTEGER` | `light_alarm BOOLEAN` |
| `acknowledged INTEGER` | `acknowledged BOOLEAN` |
| `alert_active INTEGER` | `alert_active BOOLEAN` |

### `alarm_event`

| V1 SQLite | V2 PostgreSQL |
|---|---|
| `id INTEGER PRIMARY KEY AUTOINCREMENT` | `id BIGSERIAL PRIMARY KEY` |
| `event_at TEXT` | `event_at TIMESTAMPTZ DEFAULT NOW()` |
| `event_type TEXT` | `event_type TEXT` |
| `message TEXT` | `message TEXT` |

---

## 🧩 V2 System Architecture

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
(/dev/ttyACM0 예정)
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

---

## 🚨 Alarm Threshold

| 항목 | 정상 범위 | 이상 조건 |
|---|---:|---:|
| 🌡️ 온도 | 18 ~ 28 ℃ | 18 ℃ 미만 또는 28 ℃ 초과 |
| 💧 습도 | 40 ~ 70 % | 40 % 미만 또는 70 % 초과 |
| ☀️ 조도 | 300 미만 | 300 이상 |

현재 회로에서는 **조도 센서값이 커질수록 어두운 상태**로 판단합니다.

---

## 🔌 Hardware Pin Mapping

| Component | Arduino Pin | 역할 |
|---|---|---|
| Switch | D12 | 작업자 ACK |
| DHT11 | D3 | 온도·습도 측정 |
| Buzzer | D11 | 현장 알람 |
| Red LED | D9 | 조도 이상 |
| Yellow LED | D10 | 습도 이상 |
| Green LED | D8 | 온도 이상 |
| Light Sensor | A0 | 조도 측정 |

---

## 📡 Serial Protocol

### Sensor DATA

```text
DATA,temperature,humidity,light,temp_alarm,hum_alarm,light_alarm,acknowledged,alert_active
```

Example:

```text
DATA,22.40,52.00,171,0,0,0,0,0
```

### Alarm EVENT

```text
EVENT,ALARM_START
EVENT,ACK
EVENT,RE_ALERT
EVENT,NORMAL
```

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
│       ├── db.py            # PostgreSQL 공통 연결
│       ├── init_db.py       # Schema 초기화
│       ├── middleware.py    # Serial → PostgreSQL
│       └── dashboard.py     # PostgreSQL → Streamlit
│
├── schema.sql               # PostgreSQL Schema
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

V1에서 사용하던 `data/factory_alarm.db`는 V2의 데이터 저장소가 아닙니다. 실제 데이터는 PostgreSQL Server에 저장됩니다.

---

## 🛠 V2 Tech Stack

### Hardware
- Arduino UNO R4 Minima
- DHT11
- Light Sensor
- LED
- Buzzer
- Push Switch

### Software
- WSL2 Ubuntu / Linux
- Arduino C/C++
- Python
- PySerial
- PostgreSQL
- psycopg
- python-dotenv
- pandas
- Altair
- Streamlit
- uv

---

## 🔐 Environment Variables

V2에서는 DB 접속정보와 Serial 설정을 소스코드와 분리합니다.

`.env` 예시:

```env
DATABASE_URL=postgresql://factory_user:<PASSWORD>@localhost:5432/factory_alarm
SERIAL_PORT=/dev/ttyACM0
SERIAL_BAUDRATE=115200
```

`.env`는 `.gitignore`에 포함하여 GitHub에 업로드하지 않습니다.

---

## ▶️ Current V2 Run Flow

### 1. Dependency 설치

```bash
uv sync
```

### 2. `.env` 설정

PostgreSQL 접속 정보를 `DATABASE_URL`에 지정합니다.

### 3. PostgreSQL Schema 초기화

```bash
python src/factory_environment_alarm/init_db.py
```

### 4. Dashboard 실행

```bash
python -m streamlit run src/factory_environment_alarm/dashboard.py
```

### 5. Middleware 실행

Linux에서 Arduino Serial Device 연결을 확인한 뒤 실행합니다.

```bash
python src/factory_environment_alarm/middleware.py
```

---

## ✅ Current Migration Status

완료:
- [x] WSL2 Ubuntu 개발환경 구성
- [x] PostgreSQL 설치
- [x] `factory_alarm` Database 생성
- [x] `factory_user` 연결 확인
- [x] `psycopg` 기반 `db.py` 추가
- [x] PostgreSQL용 `schema.sql` 변환
- [x] PostgreSQL용 `init_db.py` 변환
- [x] PostgreSQL용 `middleware.py` 변환
- [x] PostgreSQL용 `dashboard.py` 변환
- [x] Streamlit → PostgreSQL 조회 확인

남은 작업:
- [ ] Arduino USB Device를 WSL2에 연결
- [ ] Linux Serial Device 확인
- [ ] Middleware 실제 Serial 수신 테스트
- [ ] Arduino → PostgreSQL → Streamlit End-to-End 테스트
- [ ] V2를 별도 Repository로 분리하여 최종 보존

---

## 💡 What I Learned from V1 → V2

이번 Migration에서 중요하게 확인한 구조는 다음과 같습니다.

```text
pyserial
= Python ↔ Arduino

psycopg
= Python ↔ PostgreSQL

middleware.py
= Arduino 데이터를 해석하고 DB에 저장

db.py
= PostgreSQL 연결 방법을 공통 관리

dashboard.py
= DB 데이터를 읽어 사용자에게 시각화
```

즉, **시스템의 역할은 유지하면서 특정 기술(SQLite)을 다른 기술(PostgreSQL)로 교체할 수 있도록 계층을 분리하는 것**이 V2의 핵심 학습 내용입니다.

---

## 👩‍💻 Author

**chodaseul**  
AI Smart Manufacturing Training Project · 2026
