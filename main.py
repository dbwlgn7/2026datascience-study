import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Streamlit 기본 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="전국 학교 급식 알레르기 & 비타민 대시보드",
    page_icon="🥗",
    layout="wide",
)

st.title("🥗 전국 학교 급식 알레르기 식품 & 비타민 영양소 비교 대시보드")
st.caption(
    "원하는 전국 3개 학교의 이름을 직접 입력하여 알레르기 유발 식품 출현 빈도(묶은 가로 막대)와 비타민 제공량을 실시간 비교합니다."
)

# NEIS 알레르기 코드 매핑 (1~19번)
ALLERGY_DICT = {
    1: "난류(계란)",
    2: "우유",
    3: "메밀",
    4: "땅콩",
    5: "대두",
    6: "밀",
    7: "고등어",
    8: "게",
    9: "새우",
    10: "돼지고기",
    11: "복숭아",
    12: "토마토",
    13: "아황산류",
    14: "호두",
    15: "닭고기",
    16: "쇠고기",
    17: "오징어",
    18: "조개류",
    19: "잣",
}

# ---------------------------------------------------------
# 2. 사이드바 - 자유로운 학교 검색 및 분석 기간 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 학교 검색 & 분석 설정")
st.sidebar.caption("전국 어느 학교든 이름 일부/전체를 입력하세요.")

# 자유 입력 방식 (기본값 제공)
school_input_1 = st.sidebar.text_input("첫 번째 학교명", "인천남동고등학교")
school_input_2 = st.sidebar.text_input("두 번째 학교명", "인천고등학교")
school_input_3 = st.sidebar.text_input("세 번째 학교명", "석정여자고등학교")

start_date = st.sidebar.text_input("조회 시작일 (YYYYMMDD)", "20260901")
end_date = st.sidebar.text_input("조회 종료일 (YYYYMMDD)", "20260915")
api_key = st.sidebar.text_input(
    "NEIS API Key (선택)",
    type="password",
    help="인증키가 없으면 한 번에 최대 5건~100건까지만 조회될 수 있습니다.",
)

# ---------------------------------------------------------
# 3. NEIS API 데이터 수집 함수 (자동 검색)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def search_school_info(school_name, key=None):
    """학교 이름으로 교육청코드와 학교코드를 자동 검색"""
    if not school_name.strip():
        return None
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": school_name.strip()}
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
    """급식 식단 정보 수집"""
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


def parse_allergies(ddish_nm):
    matches = re.findall(r"\(([0-9\.]+)\)", ddish_nm)
    found_codes = set()
    for m in matches:
        for c in m.split("."):
            if c.isdigit():
                found_codes.add(int(c))
    return [ALLERGY_DICT[c] for c in sorted(list(found_codes)) if c in ALLERGY_DICT]


def clean_dish_names(ddish_nm):
    raw_dishes = ddish_nm.split("<br/>")
    return ", ".join(
        [re.sub(r"\([0-9\.]+\)", "", d).strip() for d in raw_dishes if d]
    )


def parse_nutrition(ntr_info_str):
    nutrients = {
        "비타민A(R.E)": 0.0,
        "비타민C(mg)": 0.0,
        "티아민(B1)": 0.0,
        "리보플라빈(B2)": 0.0,
        "칼슘(mg)": 0.0,
        "철분(mg)": 0.0,
    }
    if not isinstance(ntr_info_str, str):
        return nutrients

    for line in ntr_info_str.split("<br/>"):
        if ":" in line:
            parts = line.split(":")
            key = parts[0].strip()
            val_match = re.search(r"[\d\.]+", parts[1])
            if val_match:
                val = float(val_match.group())
                if "비타민A" in key:
                    nutrients["비타민A(R.E)"] = val
                elif "비타민C" in key:
                    nutrients["비타민C(mg)"] = val
                elif "티아민" in key:
                    nutrients["티아민(B1)"] = val
                elif "리보플라빈" in key:
                    nutrients["리보플라빈(B2)"] = val
                elif "칼슘" in key:
                    nutrients["칼슘(mg)"] = val
                elif "철분" in key:
                    nutrients["철분(mg)"] = val
    return nutrients


# ---------------------------------------------------------
# 4. 데이터 로드 프로세스
# ---------------------------------------------------------
user_school_inputs = [school_input_1, school_input_2, school_input_3]
target_schools_info = []
missing_schools = []

with st.spinner("입력하신 학교 정보를 조회하고 급식 데이터를 검색하는 중입니다..."):
    for s_input in user_school_inputs:
        if s_input.strip():
            info = search_school_info(s_input, api_key)
            if info:
                target_schools_info.append(info)
            else:
                missing_schools.append(s_input)

    all_data = []
    for s_info in target_schools_info:
        meals = fetch_meal_data(
            s_info["ofcdc"], s_info["code"], start_date, end_date, api_key
        )
        for m in meals:
            record = {
                "학교명": s_info["name"],
                "급식일": m["MLSV_YMD"],
                "메뉴": clean_dish_names(m["DDISH_NM"]),
                "알레르기목록": parse_allergies(m["DDISH_NM"]),
            }
            record.update(parse_nutrition(m.get("NTR_INFO", "")))
            all_data.append(record)

df = pd.DataFrame(all_data)

# ---------------------------------------------------------
# 5. 대시보드 화면 구성
# ---------------------------------------------------------
if missing_schools:
    st.warning(
        f"⚠️ 다음 학교의 정보를 찾을 수 없습니다: **{', '.join(missing_schools)}** (정확한 학교명을 입력해 주세요)"
    )

if df.empty:
    st.info(
        "💡 왼쪽 사이드바에서 비교하고 싶은 3개 학교명을 입력하고 [엔터]를 눌러주세요."
    )
else:
    df["급식일"] = pd.to_datetime(df["급식일"], format="%Y%m%d")

    # 상단 요약 카드
    col1, col2, col3 = st.columns(3)
    col1.metric("조회된 학교 수", f"{len(df['학교명'].unique())}개교")
    col2.metric("수집된 총 식단 수", f"{len(df)}건")
    col3.metric("알레르기 표기 감지 총 횟수", f"{sum(len(a) for a in df['알레르기목록'])}회")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "📊 알레르기 식품 빈도 (묶은 가로 막대)",
        "🍋 비타민 & 영양소 제공량 비교",
        "📋 상세 데이터 보기",
    ])

    # ---------------------------------------------------------
    # Tab 1: 묶은 가로 막대그래프
    # ---------------------------------------------------------
    with tab1:
        st.subheader("학교별 알레르기 유발 식품 출현 빈도 비교")
        st.caption(
            "하나의 식품(예: 계란)에 대해 선택된 학교들의 출현 횟수를 나란히 비교합니다."
        )

        allergy_rows = []
        for _, row in df.iterrows():
            for a in row["알레르기목록"]:
                allergy_rows.append({"학교명": row["학교명"], "알레르기식품": a})

        df_allergy = pd.DataFrame(allergy_rows)

        if df_allergy.empty:
            st.info("해당 기간 내 감지된 알레르기 정보가 없습니다.")
        else:
            df_counts = (
                df_allergy.groupby(["알레르기식품", "학교명"])
                .size()
                .reset_index(name="출현횟수")
            )

            fig_h_bar = px.bar(
                df_counts,
                x="출현횟수",
                y="알레르기식품",
                color="학교명",
                orientation="h",
                barmode="group",
                title="알레르기 식품별 학교 간 양적 차이 비교",
                labels={"출현횟수": "출현 횟수(회)", "알레르기식품": "알레르기 유발 식품"},
                height=650,
            )
            fig_h_bar.update_layout(
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="급식 출현 횟수 (회)",
                legend_title="학교명",
            )
            st.plotly_chart(fig_h_bar, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 2: 시험기간 비타민 & 영양소 비교
    # ---------------------------------------------------------
    with tab2:
        st.subheader("학교별 주요 비타민 & 피로회복 영양소 평균 제공량")
        st.caption(
            "시험기간 면역 및 피로 회복과 관련된 주요 영양소(비타민 C, B1, B2, 철분 등)의 평균 제공량을 비교합니다."
        )

        nut_cols = [
            "비타민A(R.E)",
            "비타민C(mg)",
            "티아민(B1)",
            "리보플라빈(B2)",
            "칼슘(mg)",
            "철분(mg)",
        ]
        df_nut_avg = df.groupby("학교명")[nut_cols].mean().reset_index()

        df_melted = pd.melt(
            df_nut_avg,
            id_vars=["학교명"],
            value_vars=["비타민C(mg)", "티아민(B1)", "리보플라빈(B2)", "철분(mg)"],
            var_name="영양소",
            value_name="평균제공량",
        )

        fig_nut = px.bar(
            df_melted,
            x="영양소",
            y="평균제공량",
            color="학교명",
            barmode="group",
            text_auto=".2f",
            title="시험기간 피로회복 관련 주요 영양소 평균 제공량 비교",
        )
        st.plotly_chart(fig_nut, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 3: 원본 데이터 표
    # ---------------------------------------------------------
    with tab3:
        st.subheader("수집된 데이터 상세 표")
        st.dataframe(df, use_container_width=True)
