#include <DHT.h>

// ======================================================
// 1. 핀 설정
// ======================================================

const int SWITCH_PIN = 12;

const int DHT_PIN = 3;
#define DHT_TYPE DHT11

const int BUZZER_PIN = 11;

const int RED_LED = 9;       // 조도 이상
const int YELLOW_LED = 10;   // 습도 이상
const int GREEN_LED = 8;     // 온도 이상

const int LIGHT_PIN = A0;

DHT dht(DHT_PIN, DHT_TYPE);


// ======================================================
// 2. 이상 기준값
// ======================================================

// 온도 정상 범위
const float TEMP_MIN = 18.0;
const float TEMP_MAX = 28.0;

// 습도 정상 범위
const float HUM_MIN = 40.0;
const float HUM_MAX = 70.0;

// 조도
// 실측:
// 가림 약 450
// 평상시 약 170
// 플래시 약 84
//
// 300 이상 = 너무 어두움
const int LIGHT_LIMIT = 300;


// ======================================================
// 3. 시간 설정
// ======================================================

// 센서 읽기 주기
const unsigned long SENSOR_INTERVAL = 2000;

// ★ 현재 테스트용: ACK 후 10초 뒤 재알림
const unsigned long RE_ALERT_TIME = 10000;

// 실제 사용할 때 10분으로 바꾸려면:
// const unsigned long RE_ALERT_TIME = 10UL * 60UL * 1000UL;


// ======================================================
// 4. 알람 종류
// ======================================================

const int ALERT_NONE = 0;
const int ALERT_FIRST = 1;
const int ALERT_REPEAT = 2;

int alertType = ALERT_NONE;


// ======================================================
// 5. 상태 변수
// ======================================================

unsigned long lastSensorTime = 0;
unsigned long acknowledgedTime = 0;

bool acknowledged = false;
bool alertActive = false;

bool tempAlarm = false;
bool humAlarm = false;
bool lightAlarm = false;

bool previousAnyAlarm = false;


// ======================================================
// 6. 스위치 상태
// ======================================================

int previousSwitchState = HIGH;


// ======================================================
// 7. 부저 상태 변수
// ======================================================

bool buzzerOn = false;

int beepCount = 0;

unsigned long buzzerTime = 0;
unsigned long patternPauseTime = 0;

bool patternPause = false;


// ======================================================
// 8. setup
// ======================================================

void setup()
{
    Serial.begin(115200);

    dht.begin();

    pinMode(SWITCH_PIN, INPUT_PULLUP);

    pinMode(BUZZER_PIN, OUTPUT);

    pinMode(RED_LED, OUTPUT);
    pinMode(YELLOW_LED, OUTPUT);
    pinMode(GREEN_LED, OUTPUT);


    digitalWrite(RED_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(GREEN_LED, LOW);

    noTone(BUZZER_PIN);


    Serial.println("Factory Environment Alarm START");
}


// ======================================================
// 9. loop
// ======================================================

void loop()
{
    unsigned long now = millis();


    // 스위치는 계속 확인
    checkSwitch(now);


    // 2초마다 센서 확인
    if (now - lastSensorTime >= SENSOR_INTERVAL)
    {
        lastSensorTime = now;

        readSensors(now);
    }


    // 부저 처리
    runBuzzer(now);
}


// ======================================================
// 10. 센서 읽기
// ======================================================

void readSensors(unsigned long now)
{
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();

    int light = analogRead(LIGHT_PIN);


    // DHT 읽기 실패
    if (isnan(humidity) || isnan(temperature))
    {
        Serial.println("ERROR,DHT_READ_FAIL");
        return;
    }


    // --------------------------------------------------
    // 이상 여부 판단
    // --------------------------------------------------

    tempAlarm =
        temperature < TEMP_MIN ||
        temperature > TEMP_MAX;


    humAlarm =
        humidity < HUM_MIN ||
        humidity > HUM_MAX;


    lightAlarm =
        light >= LIGHT_LIMIT;


    bool anyAlarm =
        tempAlarm ||
        humAlarm ||
        lightAlarm;


    // ==================================================
    // 새로운 이상 발생
    // ==================================================

    if (anyAlarm && !previousAnyAlarm)
    {
        acknowledged = false;
        alertActive = true;

        // 최초 알람 패턴
        alertType = ALERT_FIRST;

        resetBuzzerPattern();

        Serial.println("EVENT,ALARM_START");
    }


    // ==================================================
    // 전부 정상 복귀
    // ==================================================

    if (!anyAlarm)
    {
        acknowledged = false;
        alertActive = false;

        alertType = ALERT_NONE;

        turnOffAlarm();


        if (previousAnyAlarm)
        {
            Serial.println("EVENT,NORMAL");
        }
    }


    // ==================================================
    // ACK 후 10초 동안 미조치 → 재알림
    // ==================================================

    if (anyAlarm && acknowledged)
    {
        if (now - acknowledgedTime >= RE_ALERT_TIME)
        {
            acknowledged = false;
            alertActive = true;

            // 재알람 패턴
            alertType = ALERT_REPEAT;

            resetBuzzerPattern();

            Serial.println("EVENT,RE_ALERT");
        }
    }


    // ==================================================
    // LED 표시
    // ==================================================

    if (alertActive)
    {
        updateLED();
    }


    // ==================================================
    // Python으로 데이터 전송
    // ==================================================

    Serial.print("DATA,");

    Serial.print(temperature);
    Serial.print(",");

    Serial.print(humidity);
    Serial.print(",");

    Serial.print(light);
    Serial.print(",");

    Serial.print(tempAlarm);
    Serial.print(",");

    Serial.print(humAlarm);
    Serial.print(",");

    Serial.print(lightAlarm);
    Serial.print(",");

    Serial.print(acknowledged);
    Serial.print(",");

    Serial.println(alertActive);


    previousAnyAlarm = anyAlarm;
}


// ======================================================
// 11. LED 처리
// ======================================================

void updateLED()
{
    // 온도 이상 → 초록
    digitalWrite(
        GREEN_LED,
        tempAlarm ? HIGH : LOW
    );


    // 습도 이상 → 노랑
    digitalWrite(
        YELLOW_LED,
        humAlarm ? HIGH : LOW
    );


    // 조도 이상 → 빨강
    digitalWrite(
        RED_LED,
        lightAlarm ? HIGH : LOW
    );
}


// ======================================================
// 12. 스위치 처리
// ======================================================

void checkSwitch(unsigned long now)
{
    int currentSwitchState =
        digitalRead(SWITCH_PIN);


    // INPUT_PULLUP
    //
    // 안 누름 = HIGH
    // 누름 = LOW

    if (
        previousSwitchState == HIGH &&
        currentSwitchState == LOW
    )
    {
        // 현재 알람이 울릴 때만 ACK
        if (alertActive)
        {
            acknowledged = true;
            acknowledgedTime = now;

            alertActive = false;
            alertType = ALERT_NONE;

            turnOffAlarm();

            Serial.println("EVENT,ACK");
        }
    }


    previousSwitchState =
        currentSwitchState;
}


// ======================================================
// 13. 부저 패턴
// ======================================================

void runBuzzer(unsigned long now)
{
    // 알람 없으면 조용
    if (!alertActive)
    {
        noTone(BUZZER_PIN);
        return;
    }


    // --------------------------------------------------
    // 최초 알람
    //
    // 삐 - 삐 - 삐
    // --------------------------------------------------

    if (alertType == ALERT_FIRST)
    {
        runBeepPattern(
            now,
            3,      // 3번
            250,    // 삐 길이
            450,    // 삐 사이 간격
            2000    // 한 패턴 끝나고 쉬는 시간
        );
    }


    // --------------------------------------------------
    // 재알람
    //
    // 삐삐삐삐삐삐
    // --------------------------------------------------

    else if (alertType == ALERT_REPEAT)
    {
        runBeepPattern(
            now,
            6,      // 6번
            150,    // 더 짧게
            150,    // 더 빠르게
            1500    // 패턴 끝나고 쉬는 시간
        );
    }
}


// ======================================================
// 14. 공통 삐 패턴 함수
// ======================================================

void runBeepPattern(
    unsigned long now,
    int maxBeepCount,
    unsigned long beepDuration,
    unsigned long beepGap,
    unsigned long repeatPause
)
{
    // --------------------------------------------------
    // 한 묶음 끝난 뒤 쉬는 중
    // --------------------------------------------------

    if (patternPause)
    {
        if (now - patternPauseTime >= repeatPause)
        {
            patternPause = false;
            beepCount = 0;
        }

        return;
    }


    // --------------------------------------------------
    // 현재 삐 소리가 나는 중
    // --------------------------------------------------

    if (buzzerOn)
    {
        if (now - buzzerTime >= beepDuration)
        {
            noTone(BUZZER_PIN);

            buzzerOn = false;
            buzzerTime = now;

            beepCount++;
        }

        return;
    }


    // --------------------------------------------------
    // 필요한 횟수만큼 다 울림
    // --------------------------------------------------

    if (beepCount >= maxBeepCount)
    {
        patternPause = true;
        patternPauseTime = now;

        return;
    }


    // --------------------------------------------------
    // 다음 삐 시작
    // --------------------------------------------------

    if (now - buzzerTime >= beepGap)
    {
        tone(BUZZER_PIN, 1500);

        buzzerOn = true;
        buzzerTime = now;
    }
}


// ======================================================
// 15. 부저 패턴 초기화
// ======================================================

void resetBuzzerPattern()
{
    noTone(BUZZER_PIN);

    buzzerOn = false;

    beepCount = 0;

    buzzerTime = 0;

    patternPauseTime = 0;

    patternPause = false;
}


// ======================================================
// 16. LED + 부저 끄기
// ======================================================

void turnOffAlarm()
{
    digitalWrite(RED_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(GREEN_LED, LOW);

    noTone(BUZZER_PIN);

    resetBuzzerPattern();
}
