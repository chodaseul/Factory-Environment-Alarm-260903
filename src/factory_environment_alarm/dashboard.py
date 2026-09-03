import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# =====================================================
# 1. 페이지 설정
# =====================================================

st.set_page_config(
    page_title="Factory Environment Alarm",
    page_icon="🏭",
    layout="wide",
)


# =====================================================
# 2. DB 경로
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "factory_alarm.db"


# =====================================================
# 3. 환경 이상 기준값
# Arduino 코드와 동일하게 유지
# =====================================================

TEMP_MIN = 18.0
TEMP_MAX = 28.0

HUM_MIN = 40.0
HUM_MAX = 70.0

LIGHT_LIMIT = 300


# =====================================================
# 4. 알람 이벤트 표시명
# =====================================================

EVENT_LABELS = {
    "ALARM_START": "🚨 이상 발생",
    "ACK": "✅ 작업자 확인",
    "RE_ALERT": "⚠️ 미조치 재알림",
    "NORMAL": "🟢 정상 복귀",
}


# =====================================================
# 5. 사이드바
# =====================================================

st.sidebar.title("⚙️ Dashboard 설정")


# -----------------------------------------------------
# 기간 선택
# -----------------------------------------------------

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


# -----------------------------------------------------
# 데이터 개수 선택
# -----------------------------------------------------

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


# -----------------------------------------------------
# 현재 기준값 표시
# -----------------------------------------------------

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
# 6. 기간 → 조회 시작시간 변환
# =====================================================

def get_cutoff_time(period):

    if period == "최근 1시간":
        cutoff = datetime.now() - timedelta(hours=1)

    elif period == "최근 6시간":
        cutoff = datetime.now() - timedelta(hours=6)

    elif period == "최근 24시간":
        cutoff = datetime.now() - timedelta(hours=24)

    else:
        return None


    return cutoff.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# =====================================================
# 7. 센서 데이터 조회
# =====================================================

def load_sensor_data(
    limit,
    cutoff_time
):

    conn = sqlite3.connect(
        DB_PATH,
        timeout=5
    )

    try:

        if cutoff_time:

            df = pd.read_sql_query(
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
                WHERE measured_at >= ?
                ORDER BY id DESC
                LIMIT ?
                """,
                conn,
                params=(
                    cutoff_time,
                    limit
                )
            )

        else:

            df = pd.read_sql_query(
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
                LIMIT ?
                """,
                conn,
                params=(limit,)
            )

    finally:
        conn.close()


    if not df.empty:

        df["measured_at"] = pd.to_datetime(
            df["measured_at"]
        )

        # 그래프용
        # 과거 → 현재 순서
        df = df.sort_values(
            "measured_at"
        )


    return df


# =====================================================
# 8. 알람 이벤트 조회
# =====================================================

def load_alarm_events(
    cutoff_time
):

    conn = sqlite3.connect(
        DB_PATH,
        timeout=5
    )

    try:

        if cutoff_time:

            df = pd.read_sql_query(
                """
                SELECT
                    event_at,
                    event_type,
                    message
                FROM alarm_event
                WHERE event_at >= ?
                ORDER BY id DESC
                LIMIT 50
                """,
                conn,
                params=(cutoff_time,)
            )

        else:

            df = pd.read_sql_query(
                """
                SELECT
                    event_at,
                    event_type,
                    message
                FROM alarm_event
                ORDER BY id DESC
                LIMIT 50
                """,
                conn
            )

    finally:
        conn.close()


    return df


# =====================================================
# 9. 정상 / 이상 상태 표시
# =====================================================

def status_text(alarm):

    if bool(alarm):
        return "🔴 이상"

    return "🟢 정상"


# =====================================================
# 10. 빨간색 기준선 + 글자
# =====================================================

def threshold_layer(
    value,
    label
):

    threshold_df = pd.DataFrame(
        {
            "limit": [value],
            "label": [label]
        }
    )


    # 빨간 점선
    rule = (
        alt.Chart(threshold_df)
        .mark_rule(
            strokeDash=[6, 4],
            strokeWidth=1.5,
            color="red"
        )
        .encode(
            y=alt.Y(
                "limit:Q"
            )
        )
    )


    # 빨간 기준값 글자
    text = (
        alt.Chart(threshold_df)
        .mark_text(
            align="left",
            baseline="bottom",
            dx=7,
            dy=-3,
            fontSize=12,
            fontWeight="bold",
            color="red"
        )
        .encode(
            x=alt.value(5),

            y=alt.Y(
                "limit:Q"
            ),

            text=alt.Text(
                "label:N"
            )
        )
    )


    return rule + text


# =====================================================
# 11. 실시간 Dashboard
# =====================================================

@st.fragment(run_every=2)
def dashboard(
    data_limit,
    period
):

    cutoff_time = get_cutoff_time(
        period
    )


    sensor_df = load_sensor_data(
        data_limit,
        cutoff_time
    )


    event_df = load_alarm_events(
        cutoff_time
    )


    # =================================================
    # 제목
    # =================================================

    st.title(
        "🏭 Factory Environment Alarm"
    )

    st.caption(
        "온도 · 습도 · 조도 실시간 환경 모니터링"
    )


    # =================================================
    # 데이터 없음
    # =================================================

    if sensor_df.empty:

        st.warning(
            f"{period}에 저장된 센서 데이터가 없습니다."
        )

        return


    latest = sensor_df.iloc[-1]


    # =================================================
    # 전체 상태
    # =================================================

    any_alarm = (
        bool(latest["temp_alarm"])
        or bool(latest["hum_alarm"])
        or bool(latest["light_alarm"])
    )


    if any_alarm:

        if bool(latest["acknowledged"]):

            st.warning(
                "⚠️ 환경 이상 발생 / 작업자 확인 완료"
            )

        elif bool(latest["alert_active"]):

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


    # =================================================
    # 현재값 카드
    # =================================================

    col1, col2, col3 = st.columns(3)


    # 온도
    with col1:

        st.metric(
            "🌡️ 온도",
            f"{latest['temperature']:.1f} ℃"
        )

        st.caption(
            f"정상 범위 : "
            f"{TEMP_MIN:.0f} ~ {TEMP_MAX:.0f} ℃"
        )

        st.write(
            status_text(
                latest["temp_alarm"]
            )
        )


    # 습도
    with col2:

        st.metric(
            "💧 습도",
            f"{latest['humidity']:.1f} %"
        )

        st.caption(
            f"정상 범위 : "
            f"{HUM_MIN:.0f} ~ {HUM_MAX:.0f} %"
        )

        st.write(
            status_text(
                latest["hum_alarm"]
            )
        )


    # 조도
    with col3:

        st.metric(
            "☀️ 조도",
            f"{int(latest['light'])}"
        )

        st.caption(
            f"정상 범위 : {LIGHT_LIMIT} 미만"
        )

        st.write(
            status_text(
                latest["light_alarm"]
            )
        )


    # =================================================
    # 최근 측정 시각
    # =================================================

    st.caption(
        "최근 측정 : "
        + latest["measured_at"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    st.divider()


    # =================================================
    # 그래프 제목
    # =================================================

    st.subheader(
        f"📈 환경 변화 · {period}"
    )

    st.caption(
        f"현재 그래프에 표시 중인 데이터 : "
        f"{len(sensor_df)}개"
    )


    # =================================================
    # 온도 그래프
    # =================================================

    st.write(
        f"### 🌡️ 온도 "
        f"(정상 {TEMP_MIN:.0f} ~ {TEMP_MAX:.0f} ℃)"
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
                )
            ),

            y=alt.Y(
                "temperature:Q",
                title="온도 (℃)"
            ),

            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S"
                ),

                alt.Tooltip(
                    "temperature:Q",
                    title="온도",
                    format=".1f"
                )
            ]
        )
    )


    temp_min_layer = threshold_layer(
        TEMP_MIN,
        f"하한 {TEMP_MIN:.0f} ℃"
    )


    temp_max_layer = threshold_layer(
        TEMP_MAX,
        f"상한 {TEMP_MAX:.0f} ℃"
    )


    st.altair_chart(
        temp_chart
        + temp_min_layer
        + temp_max_layer,
        use_container_width=True
    )


    # =================================================
    # 습도 그래프
    # =================================================

    st.write(
        f"### 💧 습도 "
        f"(정상 {HUM_MIN:.0f} ~ {HUM_MAX:.0f} %)"
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
                )
            ),

            y=alt.Y(
                "humidity:Q",
                title="습도 (%)"
            ),

            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S"
                ),

                alt.Tooltip(
                    "humidity:Q",
                    title="습도",
                    format=".1f"
                )
            ]
        )
    )


    hum_min_layer = threshold_layer(
        HUM_MIN,
        f"하한 {HUM_MIN:.0f} %"
    )


    hum_max_layer = threshold_layer(
        HUM_MAX,
        f"상한 {HUM_MAX:.0f} %"
    )


    st.altair_chart(
        hum_chart
        + hum_min_layer
        + hum_max_layer,
        use_container_width=True
    )


    # =================================================
    # 조도 그래프
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
                )
            ),

            y=alt.Y(
                "light:Q",
                title="조도 센서값"
            ),

            tooltip=[
                alt.Tooltip(
                    "measured_at:T",
                    title="측정시간",
                    format="%Y-%m-%d %H:%M:%S"
                ),

                alt.Tooltip(
                    "light:Q",
                    title="조도"
                )
            ]
        )
    )


    light_limit_layer = threshold_layer(
        LIGHT_LIMIT,
        f"이상 기준 {LIGHT_LIMIT}"
    )


    st.altair_chart(
        light_chart
        + light_limit_layer,
        use_container_width=True
    )


    st.caption(
        "※ 조도 센서값은 숫자가 클수록 어두운 상태이며, "
        f"{LIGHT_LIMIT} 이상이면 조도 이상으로 판단합니다."
    )


    st.divider()


    # =================================================
    # 알람 이력
    # =================================================

    st.subheader(
        "🚨 알람 이력"
    )


    if event_df.empty:

        st.info(
            f"{period}에 발생한 알람 이벤트가 없습니다."
        )

    else:

        display_event_df = event_df.copy()


        # 이벤트 코드를 보기 좋은 표시명으로 변경
        display_event_df["상태"] = (
            display_event_df["event_type"]
            .map(EVENT_LABELS)
            .fillna(
                display_event_df["event_type"]
            )
        )


        display_event_df = (
            display_event_df[
                [
                    "event_at",
                    "상태",
                    "message"
                ]
            ]
            .rename(
                columns={
                    "event_at": "발생시간",
                    "message": "내용"
                }
            )
        )


        st.dataframe(
            display_event_df,
            hide_index=True,
            use_container_width=True
        )


    st.divider()


    # =================================================
    # 센서 원본 데이터
    # =================================================

    with st.expander(
        f"📋 센서 데이터 보기 ({len(sensor_df)}개)"
    ):

        recent_df = (
            sensor_df
            .sort_values(
                "measured_at",
                ascending=False
            )
            .copy()
        )


        recent_df = recent_df.rename(
            columns={
                "id": "ID",
                "measured_at": "측정시간",
                "temperature": "온도",
                "humidity": "습도",
                "light": "조도",
                "temp_alarm": "온도이상",
                "hum_alarm": "습도이상",
                "light_alarm": "조도이상",
                "acknowledged": "ACK",
                "alert_active": "알람동작"
            }
        )


        st.dataframe(
            recent_df,
            hide_index=True,
            use_container_width=True
        )


# =====================================================
# 12. Dashboard 실행
# =====================================================

dashboard(
    data_limit,
    period
)