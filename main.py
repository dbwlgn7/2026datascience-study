import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Streamlit 기본 설정 (화면이 먼저 출력되도록 최상단 배치)
# ---------------------------------------------------------
st.set_page_config(
    page_title="학교별 급식 알레르기 & 비타민 대시보드", page_icon="🥗", layout="wide"
)

st.title("🥗 NEIS 데이터 기반 학교별 알레르기 식품 & 비타민 영양소 대시보드")
st.caption(
    "3개 학교의 급식 데이터를 분석하여 알레르기 유발 식품 출현 빈도(묶은 가로 막대)와 비타민 제공량을 비교합니다."
)

# ---------------------------------------------------------
# 2. 프리셋 학교 데이터 (학교 코드 직접 등록으로 오류 방지)
# ---------------------------------------------------------
PRESET_SCHOOLS = {
    "인천남동고등학교": {"ofcdc": "E10", "code": "7310339"},
    "인천고등학교": {"ofcdc": "E10", "code": "7310058"},
    "석정여자고등학교": {"ofcdc": "E10", "code": "7310243"},
}

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
# 3. 사이드바 - 분석 및 학교 선택 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 학교 및 기간 설정")

# 기본 선택 3개교
selected_preset = st.sidebar.multiselect(
    "비교할 프리셋 학교 선택 (최대 3개)",
    options=list(PRESET_SCHOOLS.keys()),
    default=["인천남동고등학교", "인천고등학교", "석정여자고등학교"],
)

start_date = st.sidebar.text_input("조회 시작일 (YYYYMMDD)", "20260901")
end_date = st.sidebar.text_input("조회 종료일 (YYYYMMDD)", "20260915")
api_key = st.sidebar.text_input("NEIS API Key (선택)", type="password")


# ---------------------------------------------------------
# 4. 급식 데이터 수집 및 영양소/알레르기 파싱 함수
# ---------------------------------------------------------
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
# 5. 데이터 처리 및 대시보드 생성
# ---------------------------------------------------------
all_data = []

with st.spinner("선택한 학교의 급식 데이터를 불러오는 중입니다..."):
    for s_name in selected_preset:
        info = PRESET_SCHOOLS[s_name]
        meals = fetch_meal_data(
            info["ofcdc"], info["code"], start_date, end_date, api_key
        )
        for m in meals:
            record = {
                "학교명": s_name,
                "급식일": m["MLSV_YMD"],
                "메뉴": clean_dish_names(m["DDISH_NM"]),
                "알레르기목록": parse_allergies(m["DDISH_NM"]),
            }
            record.update(parse_nutrition(m.get("NTR_INFO", "")))
            all_data.append(record)

df = pd.DataFrame(all_data)

if df.empty:
    st.warning(
        "급식 데이터를 불러올 수 없습니다. 조회 기간 또는 네트워크 상태를 확인하세요."
    )
else:
    df["급식일"] = pd.to_datetime(df["급식일"], format="%Y%m%d")

    # 상단 카드
    col1, col2, col3 = st.columns(3)
    col1.metric("선택된 학교 수", f"{len(selected_preset)}개교")
    col2.metric("총 수집 식단 수", f"{len(df)}건")
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

        allergy_rows = []
        for _, row in df.iterrows():
            for a in row["알레르기목록"]:
                allergy_rows.append({"학교명": row["학교명"], "알레르기식품": a})

        df_allergy = pd.DataFrame(allergy_rows)

        if df_allergy.empty:
            st.info("해당 기간 내 감지된 알레르기 항목이 없습니다.")
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
                title="알레르기 식품별 학교 간 빈도 비교 (묶은 가로 막대)",
                labels={"출현횟수": "출현 횟수(회)", "알레르기식품": "알레르기 식품명"},
                height=600,
            )
            fig_h_bar.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_h_bar, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 2: 비타민 & 영양소 분석
    # ---------------------------------------------------------
    with tab2:
        st.subheader("학교별 주요 비타민 & 피로회복 영양소 평균 제공량")

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
            title="시험기간 피로회복 관련 영양소 평균 제공량 비교",
        )
        st.plotly_chart(fig_nut, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 3: 원본 데이터 표
    # ---------------------------------------------------------
    with tab3:
        st.subheader("수집된 데이터 상세 표")
        st.dataframe(df, use_container_width=True)
