import os

import serial

from factory_environment_alarm.db import get_connection


# =====================================================
# 1. Arduino Serial 설정
# =====================================================

# Linux 기본값
# 필요하면 .env에서 SERIAL_PORT로 변경 가능
PORT = os.getenv(
    "SERIAL_PORT",
    "/dev/ttyACM0",
)

BAUDRATE = int(
    os.getenv(
        "SERIAL_BAUDRATE",
        "115200",
    )
)


# =====================================================
# 2. 센서 데이터 저장
# =====================================================

def save_sensor_data(
    temperature,
    humidity,
    light,
    temp_alarm,
    hum_alarm,
    light_alarm,
    acknowledged,
    alert_active,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sensor_data
            (
                temperature,
                humidity,
                light,
                temp_alarm,
                hum_alarm,
                light_alarm,
                acknowledged,
                alert_active
            )
            VALUES
            (
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                temperature,
                humidity,
                light,
                bool(temp_alarm),
                bool(hum_alarm),
                bool(light_alarm),
                bool(acknowledged),
                bool(alert_active),
            ),
        )


# =====================================================
# 3. 알람 이벤트 저장
# =====================================================

def save_alarm_event(event_type):
    messages = {
        "ALARM_START": "환경 이상 발생",
        "ACK": "작업자 알람 확인",
        "RE_ALERT": "미조치 재알림",
        "NORMAL": "환경 정상 복귀",
    }

    message = messages.get(
        event_type,
        event_type,
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO alarm_event
            (
                event_type,
                message
            )
            VALUES
            (
                %s,
                %s
            )
            """,
            (
                event_type,
                message,
            ),
        )


# =====================================================
# 4. DATA 처리
# =====================================================

def process_data(line):
    parts = line.split(",")

    # DATA + 값 8개 = 총 9개
    if len(parts) != 9:
        print(
            "DATA 형식 오류 :",
            line,
        )
        return

    try:
        temperature = float(
            parts[1]
        )

        humidity = float(
            parts[2]
        )

        light = int(
            parts[3]
        )

        temp_alarm = int(
            parts[4]
        )

        hum_alarm = int(
            parts[5]
        )

        light_alarm = int(
            parts[6]
        )

        acknowledged = int(
            parts[7]
        )

        alert_active = int(
            parts[8]
        )

        save_sensor_data(
            temperature,
            humidity,
            light,
            temp_alarm,
            hum_alarm,
            light_alarm,
            acknowledged,
            alert_active,
        )

        print(
            f"[DATA 저장] "
            f"온도={temperature} / "
            f"습도={humidity} / "
            f"조도={light}"
        )

    except ValueError:
        print(
            "값 변환 오류 :",
            line,
        )


# =====================================================
# 5. EVENT 처리
# =====================================================

def process_event(line):
    parts = line.split(",")

    if len(parts) != 2:
        print(
            "EVENT 형식 오류 :",
            line,
        )
        return

    event_type = parts[1]

    save_alarm_event(
        event_type
    )

    print(
        f"[EVENT 저장] "
        f"{event_type}"
    )


# =====================================================
# 6. Arduino 데이터 수신
# =====================================================

def run():
    print(
        "======================================"
    )
    print(
        "Factory Environment Alarm Middleware"
    )
    print(
        "======================================"
    )

    print(
        "Database : PostgreSQL"
    )

    print(
        f"PORT     : {PORT}"
    )

    print(
        f"BAUDRATE : {BAUDRATE}"
    )

    print(
        "Arduino 연결 중..."
    )

    ser = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1,
    )

    print(
        "Arduino 연결 완료!"
    )

    print(
        "데이터 수신 시작...\n"
    )

    try:
        while True:
            line = (
                ser.readline()
                .decode(
                    "utf-8",
                    errors="ignore",
                )
                .strip()
            )

            if not line:
                continue

            print(
                "Arduino >",
                line,
            )

            # 센서값
            if line.startswith(
                "DATA,"
            ):
                process_data(
                    line
                )

            # 이벤트
            elif line.startswith(
                "EVENT,"
            ):
                process_event(
                    line
                )

            # DHT 오류
            elif line.startswith(
                "ERROR,"
            ):
                print(
                    "[Arduino ERROR]",
                    line,
                )

    except KeyboardInterrupt:
        print(
            "\nMiddleware 종료"
        )

    finally:
        ser.close()

        print(
            "Serial 연결 종료"
        )


# =====================================================
# 7. 직접 실행
# =====================================================

if __name__ == "__main__":
    run()