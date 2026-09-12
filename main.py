import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Streamlit 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="급식 잔반 감축 대시보드", page_icon="🍱", layout="wide"
)

st.title("🍱 NEIS 데이터 기반 학교별 급식 잔반 위험도 대시보드")
st.caption(
    "3개 고등학교(인천남동고, 인천고, 석정여고)의 급식 데이터를 분석하여 잔반 위험도를 예보하고 영양 밸런스를 비교합니다."
)

# ---------------------------------------------------------
# 2. 사이드바 - 설정 메뉴
# ---------------------------------------------------------
st.sidebar.header("⚙️ 분석 설정")
start_date = st.sidebar.text_input("조회 시작일 (YYYYMMDD)", "20260901")
end_date = st.sidebar.text_input("조회 종료일 (YYYYMMDD)", "20260915")
api_key = st.sidebar.text_input(
    "NEIS API Key (선택)",
    type="password",
    help="인증키가 없으면 조회 결과가 기본 5건으로 제한됩니다.",
)

target_schools = ["인천남동고등학교", "인천고등학교", "석정여고"]


# ---------------------------------------------------------
# 3. NEIS API 데이터 수집 & 전처리 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_school_code(school_name, key=None):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": school_name}
    if key:
        params["KEY"] = key
    try:
        res = requests.get(url, params=params, timeout=5).json()
        if "schoolInfo" in res:
            row = res["schoolInfo"][1]["row"][0]
            return {
                "name": row["SCHUL_NM"],
                "ofcdc": row["ATPT_OFCDC_SC_CODE"],
                "code": row["SD_SCHUL_CODE"],
            }
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def fetch_meal_data(ofcdc, code, from_ymd, to_ymd, key=None):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ofcdc,
        "SD_SCHUL_CODE": code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
        "pSize": 100,
    }
    if key:
        params["KEY"] = key
    try:
        res = requests.get(url, params=params, timeout=5).json()
        if "mealServiceDietInfo" in res:
            return res["mealServiceDietInfo"][1]["row"]
    except Exception:
        pass
    return []


def clean_and_score_meal(ddish_nm):
    raw_dishes = ddish_nm.split("<br/>")
    cleaned_dishes = []
    for dish in raw_dishes:
        clean_dish = re.sub(r"\([0-9\.]+\)", "", dish).strip()
        if clean_dish:
            cleaned_dishes.append(clean_dish)

    # 잔반 위험도 점수 계산 로직
    high_risk_kw = ["무침", "나물", "청국장", "조림", "시래기", "숙채"]
    low_risk_kw = ["돈가스", "치킨", "스파게티", "마라", "불고기", "튀김"]

    score = 2.5
    for dish in cleaned_dishes:
        for kw in high_risk_kw:
            if kw in dish:
                score += 0.6
        for kw in low_risk_kw:
            if kw in dish:
                score -= 0.4

    final_score = round(max(1.0, min(5.0, score)), 1)
    return ", ".join(cleaned_dishes), final_score


# ---------------------------------------------------------
# 4. 데이터 로드 및 처리
# ---------------------------------------------------------
with st.spinner("NEIS 급식 데이터를 수집하고 분석하는 중입니다..."):
    all_data = []

    for s_name in target_schools:
        s_info = fetch_school_code(s_name, api_key)
        if s_info:
            meals = fetch_meal_data(
                s_info["ofcdc"], s_info["code"], start_date, end_date, api_key
            )
            for m in meals:
                dishes_str, risk_score = clean_and_score_meal(m["DDISH_NM"])

                cal_match = re.search(r"[\d\.]+", m.get("CAL_INFO", "0"))
                cal_val = float(cal_match.group()) if cal_match else 0.0

                all_data.append({
                    "학교명": s_info["name"],
                    "급식일": m["MLSV_YMD"],
                    "메뉴": dishes_str,
                    "잔반위험도": risk_score,
                    "칼로리(kcal)": cal_val,
                })

df = pd.DataFrame(all_data)

# ---------------------------------------------------------
# 5. Streamlit 화면 구성 (대시보드)
# ---------------------------------------------------------
if df.empty:
    st.warning(
        "조회된 급식 데이터가 없습니다. 날짜 범위나 학교명을 확인해 주세요."
    )
else:
    # 날짜 정렬
    df["급식일"] = pd.to_datetime(df["급식일"], format="%Y%m%d")
    df = df.sort_values("급식일")

    # 상단 KPI 카즈
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 수집 식단 수", f"{len(df)}개")
    with col2:
        st.metric("전체 평균 잔반 위험도", f"{df['잔반위험도'].mean():.2f} / 5.0")
    with col3:
        high_risk_count = len(df[df["잔반위험도"] >= 3.5])
        st.metric("고위험 식단(3.5 이상)", f"{high_risk_count}건", delta_color="inverse")
    with col4:
        st.metric("평균 칼로리", f"{df['칼로리(kcal)'].mean():.0f} kcal")

    st.markdown("---")

    # 탭 메뉴 구성
    tab1, tab2, tab3 = st.tabs([
        "📅 일자별 잔반 위험도 예보",
        "🏫 학교별 잔반 & 칼로리 비교",
        "📋 상세 식단 데이터 보기",
    ])

    # Tab 1: 일자별 잔반 위험도 트렌드 (꺾은선 그래프)
    with tab1:
        st.subheader("일자별 학교 급식 잔반 위험도 추이")
        fig_line = px.line(
            df,
            x="급식일",
            y="잔반위험도",
            color="학교명",
            markers=True,
            hover_data=["메뉴", "칼로리(kcal)"],
            title="날짜별 잔반 위험도 (높을수록 잔반 가능성 증가)",
        )
        fig_line.add_hline(
            y=3.5,
            line_dash="dash",
            line_color="red",
            annotation_text="고위험 기준선(3.5)",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # Tab 2: 학교별 비교 분석 (막대 그래프)
    with tab2:
        st.subheader("학교별 평균 잔반 위험도 및 칼로리 비교")
        col_t2_1, col_t2_2 = st.columns(2)

        with col_t2_1:
            df_avg = (
                df.groupby("학교명")["잔반위험도"]
                .mean()
                .reset_index()
            )
            fig_bar1 = px.bar(
                df_avg,
                x="학교명",
                y="잔반위험도",
                color="학교명",
                title="학교별 평균 잔반 위험도",
            )
            st.plotly_chart(fig_bar1, use_container_width=True)

        with col_t2_2:
            fig_scatter = px.scatter(
                df,
                x="칼로리(kcal)",
                y="잔반위험도",
                color="학교명",
                hover_data=["메뉴"],
                title="칼로리와 잔반 위험도 간 상관관계",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    # Tab 3: 원본 데이터 테이블
    with tab3:
        st.subheader("수집된 급식 데이터 전체 목록")
        # 위험도 높은 순서로 보기 옵션
        sort_by_risk = st.checkbox("잔반 위험도 높은 순으로 정렬")
        if sort_by_risk:
            st.dataframe(
                df.sort_values("잔반위험도", ascending=False),
                use_container_width=True,
            )
        else:
            st.dataframe(df, use_container_width=True)
