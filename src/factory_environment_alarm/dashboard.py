from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from factory_environment_alarm.db import get_connection


# =====================================================
# 1. 페이지 설정
# =====================================================

st.set_page_config(
    page_title="Factory Environment Alarm",
    page_icon="🏭",
    layout="wide",
)


# =====================================================
# 2. 환경 이상 기준값
# Arduino 코드와 동일하게 유지
# =====================================================

TEMP_MIN = 18.0
TEMP_MAX = 28.0

HUM_MIN = 40.0
HUM_MAX = 70.0

LIGHT_LIMIT = 300


# =====================================================
# 3. 알람 이벤트 표시명
# =====================================================

EVENT_LABELS = {
    "ALARM_START": "🚨 이상 발생",
    "ACK": "✅ 작업자 확인",
    "RE_ALERT": "⚠️ 미조치 재알림",
    "NORMAL": "🟢 정상 복귀",
}


# =====================================================
# 4. 사이드바
# =====================================================

st.sidebar.title("⚙️ Dashboard 설정")

period = st.sidebar.selectbox(
    "조회 기간",
    [
        "최근 1시간",
        "최근 6시간",
        "최근 24시간",
        "전체",
    ],
    index=1,
)

data_limit = st.sidebar.slider(
    "조회 데이터 수",
    min_value=20,
    max_value=1000,
    value=300,
    step=20,
)

st.sidebar.caption(
    f"선택한 기간 내에서 최근 {data_limit}개의 "
    "센서 데이터를 표시합니다."
)

st.sidebar.divider()

st.sidebar.subheader("🚨 현재 알람 기준")

st.sidebar.write(
    f"🌡️ 온도 : {TEMP_MIN:.0f} ~ {TEMP_MAX:.0f} ℃"
)

st.sidebar.write(
    f"💧 습도 : {HUM_MIN:.0f} ~ {HUM_MAX:.0f} %"
)

st.sidebar.write(
    f"☀️ 조도 : {LIGHT_LIMIT} 미만"
)

st.sidebar.caption(
    "※ 조도 센서값은 숫자가 클수록 어두운 상태입니다."
)


# =====================================================
# 5. 조회 시작시간 계산
# =====================================================

def get_cutoff_time(period):
    now = datetime.now().astimezone()

    if period == "최근 1시간":
        return now - timedelta(hours=1)

    if period == "최근 6시간":
        return now - timedelta(hours=6)

    if period == "최근 24시간":
        return now - timedelta(hours=24)

    return None


# =====================================================
# 6. PostgreSQL 결과 → DataFrame
# =====================================================

def query_dataframe(
    query,
    params=None,
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                params or (),
            )

            rows = cursor.fetchall()

            columns = [
                column.name
                for column in cursor.description
            ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


# =====================================================
# 7. 센서 데이터 조회
# =====================================================

def load_sensor_data(
    limit,
    cutoff_time,
):
    if cutoff_time:
        df = query_dataframe(
            """
            SELECT
                id,
                measured_at,
                temperature,
                humidity,
                light,
                temp_alarm,
                hum_alarm,
                light_alarm,
                acknowledged,
                alert_active
            FROM sensor_data
            WHERE measured_at >= %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (
                cutoff_time,
                limit,
            ),
        )

    else:
        df = query_dataframe(
            """
            SELECT
                id,
                measured_at,
                temperature,
                humidity,
                light,
                temp_alarm,
                hum_alarm,
                light_alarm,
                acknowledged,
                alert_active
            FROM sensor_data
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

    if not df.empty:
        df["measured_at"] = pd.to_datetime(
            df["measured_at"]
        )

        # 그래프는 과거 → 현재 순서
        df = df.sort_values(
            "measured_at"
        )

    return df


# =====================================================
# 8. 알람 이벤트 조회
# =====================================================

def load_alarm_events(
    cutoff_time,
):
    if cutoff_time:
        df = query_dataframe(
            """
            SELECT
                event_at,
                event_type,
                message
            FROM alarm_event
            WHERE event_at >= %s
            ORDER BY id DESC
            LIMIT 50
            """,
            (cutoff_time,),
        )

    else:
        df = query_dataframe(
            """
            SELECT
                event_at,
                event_type,
                message
            FROM alarm_event
            ORDER BY id DESC
            LIMIT 50
            """
        )

    if not df.empty:
        df["event_at"] = pd.to_datetime(
            df["event_at"]
        )

    return df


# =====================================================
# 9. 정상 / 이상 텍스트
# =====================================================

def status_text(alarm):
    if bool(alarm):
        return "🔴 이상"

    return "🟢 정상"


# =====================================================
# 10. 그래프 Threshold Layer
# =====================================================

def threshold_layer(
    value,
    label,
):
    threshold_df = pd.DataFrame(
        {
            "limit": [value],
            "label": [label],
        }
    )

    rule = (
        alt.Chart(threshold_df)
        .mark_rule(
            strokeDash=[6, 4],
            strokeWidth=1.5,
            color="red",
        )
        .encode(
            y=alt.Y(
                "limit:Q"
            )
        )
    )

    text = (
        alt.Chart(threshold_df)
        .mark_text(
            align="left",
            baseline="bottom",
            dx=7,
            dy=-3,
            fontSize=12,
            fontWeight="bold",
            color="red",
        )
        .encode(
            x=alt.value(5),
            y=alt.Y(
                "limit:Q"
            ),
            text=alt.Text(
                "label:N"
            ),
        )
    )

    return rule + text


# =====================================================
# 11. Dashboard
# =====================================================

@st.fragment(
    run_every=2
)
def dashboard(
    data_limit,
    period,
):
    cutoff_time = get_cutoff_time(
        period
    )

    sensor_df = load_sensor_data(
        data_limit,
        cutoff_time,
    )

    event_df = load_alarm_events(
        cutoff_time
    )

    # -------------------------------------------------
    # 제목
    # -------------------------------------------------

    st.title(
        "🏭 Factory Environment Alarm"
    )

    st.caption(
        "Linux + PostgreSQL 기반 "
        "온도 · 습도 · 조도 실시간 환경 모니터링"
    )

    # -------------------------------------------------
    # 데이터 없음
    # -------------------------------------------------

    if sensor_df.empty:
        st.warning(
            f"{period}에 저장된 센서 데이터가 없습니다."
        )

        st.info(
            "Middleware에서 센서 데이터를 "
            "PostgreSQL로 저장하면 자동으로 표시됩니다."
        )

        return

    latest = sensor_df.iloc[-1]

    # -------------------------------------------------
    # 전체 상태
    # -------------------------------------------------

    any_alarm = (
        bool(latest["temp_alarm"])
        or bool(latest["hum_alarm"])
        or bool(latest["light_alarm"])
    )

    if any_alarm:

        if bool(
            latest["acknowledged"]
        ):
            st.warning(
                "⚠️ 환경 이상 발생 / 작업자 확인 완료"
            )

        elif bool(
            latest["alert_active"]
        ):
            st.error(
                "🚨 환경 이상 알람 발생"
            )

        else:
            st.warning(
                "⚠️ 환경 이상 상태"
            )

    else:
        st.success(
            "✅ 현재 환경 상태 정상"
        )

    # -------------------------------------------------
    # 현재 센서값
    # -------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🌡️ 온도",
            f"{latest['temperature']:.1f} ℃",
        )

        st.caption(
            f"정상 범위 : "
            f"{TEMP_MIN:.0f} ~ "
            f"{TEMP_MAX:.0f} ℃"
        )

        st.write(
            status_text(
                latest["temp_alarm"]
            )
        )

    with col2:
        st.metric(
            "💧 습도",
            f"{latest['humidity']:.1f} %",
        )

        st.caption(
            f"정상 범위 : "
            f"{HUM_MIN:.0f} ~ "
            f"{HUM_MAX:.0f} %"
        )

        st.write(
            status_text(
                latest["hum_alarm"]
            )
        )

    with col3:
        st.metric(
            "☀️ 조도",
            f"{int(latest['light'])}",
        )

        st.caption(
            f"정상 범위 : "
            f"{LIGHT_LIMIT} 미만"
        )

        st.write(
            status_text(
                latest["light_alarm"]
            )
        )

    st.caption(
        "최근 측정 : "
        + latest["measured_at"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    st.divider()

    # -------------------------------------------------
    # 환경 변화
    # -------------------------------------------------

    st.subheader(
        f"📈 환경 변화 · {period}"
    )

    st.caption(
        f"현재 그래프에 표시 중인 데이터 : "
        f"{len(sensor_df)}개"
    )

    # =================================================
    # 온도
    # =================================================

    st.write(
        f"### 🌡️ 온도 "
        f"(정상 {TEMP_MIN:.0f} ~ "
        f"{TEMP_MAX:.0f} ℃)"
    )

    temp_chart = (
        alt.Chart(sensor_df)
        .mark_line(
            point=True
        )
        .encode(
            x=alt.X(
                "measured_at:T",
                title="시간",
                axis=alt.Axis(
                    format="%H:%M:%S"
                ),
            ),
            y=alt.Y(
                "temperature:Q",
                title="온도 (℃)",
            ),
            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S",
                ),
                alt.Tooltip(
                    "temperature:Q",
                    title="온도",
                    format=".1f",
                ),
            ],
        )
    )

    st.altair_chart(
        temp_chart
        + threshold_layer(
            TEMP_MIN,
            f"하한 {TEMP_MIN:.0f} ℃",
        )
        + threshold_layer(
            TEMP_MAX,
            f"상한 {TEMP_MAX:.0f} ℃",
        ),
        use_container_width=True,
    )

    # =================================================
    # 습도
    # =================================================

    st.write(
        f"### 💧 습도 "
        f"(정상 {HUM_MIN:.0f} ~ "
        f"{HUM_MAX:.0f} %)"
    )

    hum_chart = (
        alt.Chart(sensor_df)
        .mark_line(
            point=True
        )
        .encode(
            x=alt.X(
                "measured_at:T",
                title="시간",
                axis=alt.Axis(
                    format="%H:%M:%S"
                ),
            ),
            y=alt.Y(
                "humidity:Q",
                title="습도 (%)",
            ),
            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S",
                ),
                alt.Tooltip(
                    "humidity:Q",
                    title="습도",
                    format=".1f",
                ),
            ],
        )
    )

    st.altair_chart(
        hum_chart
        + threshold_layer(
            HUM_MIN,
            f"하한 {HUM_MIN:.0f} %",
        )
        + threshold_layer(
            HUM_MAX,
            f"상한 {HUM_MAX:.0f} %",
        ),
        use_container_width=True,
    )

    # =================================================
    # 조도
    # =================================================

    st.write(
        f"### ☀️ 조도 "
        f"(정상 {LIGHT_LIMIT} 미만)"
    )

    light_chart = (
        alt.Chart(sensor_df)
        .mark_line(
            point=True
        )
        .encode(
            x=alt.X(
                "measured_at:T",
                title="시간",
                axis=alt.Axis(
                    format="%H:%M:%S"
                ),
            ),
            y=alt.Y(
                "light:Q",
                title="조도 센서값",
            ),
            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S",
                ),
                alt.Tooltip(
                    "light:Q",
                    title="조도",
                ),
            ],
        )
    )

    st.altair_chart(
        light_chart
        + threshold_layer(
            LIGHT_LIMIT,
            f"기준 {LIGHT_LIMIT}",
        ),
        use_container_width=True,
    )

    st.divider()

    # =================================================
    # Alarm History
    # =================================================

    st.subheader(
        "🚨 Alarm Event History"
    )

    if event_df.empty:
        st.info(
            "조회 기간 내 알람 이벤트가 없습니다."
        )

    else:
        event_display = event_df.copy()

        event_display[
            "event"
        ] = event_display[
            "event_type"
        ].map(
            EVENT_LABELS
        ).fillna(
            event_display["event_type"]
        )

        event_display[
            "event_at"
        ] = event_display[
            "event_at"
        ].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        event_display = event_display[
            [
                "event_at",
                "event",
                "message",
            ]
        ]

        event_display.columns = [
            "발생시각",
            "이벤트",
            "내용",
        ]

        st.dataframe(
            event_display,
            hide_index=True,
            use_container_width=True,
        )


# =====================================================
# 실행
# =====================================================

dashboard(
    data_limit,
    period,
)