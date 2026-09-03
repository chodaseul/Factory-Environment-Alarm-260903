import sqlite3
import serial

from datetime import datetime
from pathlib import Path


# =====================================================
# 1. 경로 설정
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "factory_alarm.db"


# =====================================================
# 2. Arduino Serial 설정
# =====================================================

# ★ Arduino IDE에서 보이는 포트 번호로 바꾸기
PORT = "COM8"

BAUDRATE = 115200


# =====================================================
# 3. 센서 데이터 저장
# =====================================================

def save_sensor_data(
    temperature,
    humidity,
    light,
    temp_alarm,
    hum_alarm,
    light_alarm,
    acknowledged,
    alert_active
):
    measured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute(
            """
            INSERT INTO sensor_data
            (
                measured_at,
                temperature,
                humidity,
                light,
                temp_alarm,
                hum_alarm,
                light_alarm,
                acknowledged,
                alert_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measured_at,
                temperature,
                humidity,
                light,
                temp_alarm,
                hum_alarm,
                light_alarm,
                acknowledged,
                alert_active
            )
        )

        conn.commit()

    finally:
        conn.close()


# =====================================================
# 4. 알람 이벤트 저장
# =====================================================

def save_alarm_event(event_type):
    event_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    # 화면에서 보기 좋게 메시지 변환
    messages = {
        "ALARM_START": "환경 이상 발생",
        "ACK": "작업자 알람 확인",
        "RE_ALERT": "미조치 재알림",
        "NORMAL": "환경 정상 복귀"
    }


    message = messages.get(
        event_type,
        event_type
    )


    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute(
            """
            INSERT INTO alarm_event
            (
                event_at,
                event_type,
                message
            )
            VALUES (?, ?, ?)
            """,
            (
                event_at,
                event_type,
                message
            )
        )

        conn.commit()

    finally:
        conn.close()


# =====================================================
# 5. DATA 처리
# =====================================================

def process_data(line):
    parts = line.split(",")


    # DATA + 값 8개 = 총 9개
    if len(parts) != 9:
        print("DATA 형식 오류 :", line)
        return


    try:
        temperature = float(parts[1])

        humidity = float(parts[2])

        light = int(parts[3])

        temp_alarm = int(parts[4])

        hum_alarm = int(parts[5])

        light_alarm = int(parts[6])

        acknowledged = int(parts[7])

        alert_active = int(parts[8])


        save_sensor_data(
            temperature,
            humidity,
            light,
            temp_alarm,
            hum_alarm,
            light_alarm,
            acknowledged,
            alert_active
        )


        print(
            f"[DATA 저장] "
            f"온도={temperature} / "
            f"습도={humidity} / "
            f"조도={light}"
        )


    except ValueError:
        print("값 변환 오류 :", line)


# =====================================================
# 6. EVENT 처리
# =====================================================

def process_event(line):
    parts = line.split(",")


    if len(parts) != 2:
        print("EVENT 형식 오류 :", line)
        return


    event_type = parts[1]


    save_alarm_event(event_type)


    print(
        f"[EVENT 저장] {event_type}"
    )


# =====================================================
# 7. Arduino 데이터 수신
# =====================================================

def run():
    print("======================================")
    print("Factory Environment Alarm Middleware")
    print("======================================")
    print(f"DB   : {DB_PATH}")
    print(f"PORT : {PORT}")
    print("Arduino 연결 중...")


    ser = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1
    )


    print("Arduino 연결 완료!")
    print("데이터 수신 시작...\n")


    try:
        while True:

            line = (
                ser.readline()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
                .strip()
            )


            if not line:
                continue


            # Arduino가 보내는 원본도 확인
            print("Arduino >", line)


            # 센서값
            if line.startswith("DATA,"):
                process_data(line)


            # 이벤트
            elif line.startswith("EVENT,"):
                process_event(line)


            # DHT 오류
            elif line.startswith("ERROR,"):
                print(
                    "[Arduino ERROR]",
                    line
                )


    except KeyboardInterrupt:

        print("\nMiddleware 종료")


    finally:

        ser.close()

        print("Serial 연결 종료")


# =====================================================
# 8. 직접 실행
# =====================================================

if __name__ == "__main__":
    run()