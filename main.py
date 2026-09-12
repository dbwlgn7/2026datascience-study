\import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Streamlit 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="학교별 급식 알레르기 & 비타민 영양소 대시보드",
    page_icon="🥗",
    layout="wide",
)

st.title("🥗 NEIS 데이터 기반 학교별 알레르기 식품 & 비타민 영양소 비교 대시보드")
st.caption(
    "선택한 3개 학교의 급식 데이터를 분석하여 알레르기 유발 식품 출현 빈도와 시험기간 비타민/영양소 공급량을 비교합니다."
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
# 2. 사이드바 - 학교 3개 선택 및 기간 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 학교 선택 및 분석 설정")

col_s1, col_s2, col_s3 = st.sidebar.container(), st.sidebar.container(), st.sidebar.container()

school_1 = st.sidebar.text_input("첫 번째 학교", "인천남동고등학교")
school_2 = st.sidebar.text_input("두 번째 학교", "인천고등학교")
school_3 = st.sidebar.text_input("세 번째 학교", "석정여고")

target_schools = [s.strip() for s in [school_1, school_2, school_3] if s.strip()]

start_date = st.sidebar.text_input("조회 시작일 (YYYYMMDD)", "20260901")
end_date = st.sidebar.text_input("조회 종료일 (YYYYMMDD)", "20260915")
api_key = st.sidebar.text_input(
    "NEIS API Key (선택)",
    type="password",
    help="인증키가 없으면 1회 조회 시 결과가 제한될 수 있습니다.",
)


# ---------------------------------------------------------
# 3. 데이터 수집 및 파싱 함수
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


# 알레르기 번호 추출 함수
def parse_allergies(ddish_nm):
    matches = re.findall(r"\(([0-9\.]+)\)", ddish_nm)
    found_codes = set()
    for m in matches:
        codes = m.split(".")
        for c in codes:
            if c.isdigit():
                found_codes.add(int(c))
    allergy_names = [
        ALLERGY_DICT[c] for c in sorted(list(found_codes)) if c in ALLERGY_DICT
    ]
    return allergy_names


# 메뉴 텍스트 정제 함수
def clean_dish_names(ddish_nm):
    raw_dishes = ddish_nm.split("<br/>")
    cleaned = [re.sub(r"\([0-9\.]+\)", "", d).strip() for d in raw_dishes if d]
    return ", ".join(cleaned)


# 영양소 정보(NTR_INFO) 파싱 함수
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

    lines = ntr_info_str.split("<br/>")
    for line in lines:
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
# 4. 데이터 로드 및 수집 실행
# ---------------------------------------------------------
with st.spinner("선택하신 3개 학교의 NEIS 급식 데이터를 수집 중입니다..."):
    all_data = []

    for s_name in target_schools:
        s_info = fetch_school_code(s_name, api_key)
        if s_info:
            meals = fetch_meal_data(
                s_info["ofcdc"], s_info["code"], start_date, end_date, api_key
            )
            for m in meals:
                dishes_str = clean_dish_names(m["DDISH_NM"])
                allergies = parse_allergies(m["DDISH_NM"])
                nutrients = parse_nutrition(m.get("NTR_INFO", ""))

                cal_match = re.search(r"[\d\.]+", m.get("CAL_INFO", "0"))
                cal_val = float(cal_match.group()) if cal_match else 0.0

                record = {
                    "학교명": s_info["name"],
                    "급식일": m["MLSV_YMD"],
                    "메뉴": dishes_str,
                    "알레르기목록": allergies,
                    "칼로리(kcal)": cal_val,
                }
                record.update(nutrients)
                all_data.append(record)

df = pd.DataFrame(all_data)

# ---------------------------------------------------------
# 5. 대시보드 화면 구성
# ---------------------------------------------------------
if df.empty:
    st.warning("선택한 학교의 급식 데이터를 불러오지 못했습니다. 학교명 및 조회 날짜를 확인해 주세요.")
else:
    df["급식일"] = pd.to_datetime(df["급식일"], format="%Y%m%d")
    df = df.sort_values("급식일")

    # 상단 요약 카즈
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("비교 학교 수", f"{len(df['학교명'].unique())}개교")
    with col2:
        st.metric("총 식단 건수", f"{len(df)}건")
    with col3:
        # 알레르기 항목 총 감지 수
        total_allergies = sum(len(a) for a in df["알레르기목록"])
        st.metric("감지된 알레르기 성분", f"{total_allergies}회")
    with col4:
        st.metric("평균 칼로리", f"{df['칼로리(kcal)'].mean():.0f} kcal")

    st.markdown("---")

    # 탭 메뉴
    tab1, tab2, tab3 = st.tabs([
        "📊 알레르기 식품 빈도 비교 (묶은 가로 막대)",
        "🍋 시험기간 비타민 & 영양소 분석",
        "📋 상세 식단 & 알레르기 데이터",
    ])

    # ---------------------------------------------------------
    # Tab 1: 묶은 가로 막대그래프 (Grouped Horizontal Bar Chart)
    # ---------------------------------------------------------
    with tab1:
        st.subheader("학교별 알레르기 유발 식품 출현 빈도 비교")
        st.caption("식품(예: 계란, 밀)별로 각 학교의 출현 횟수를 나란히 비교합니다.")

        # 알레르기 데이터를 가공하여 카운트 테이블 생성
        allergy_rows = []
        for _, row in df.iterrows():
            for allergy_item in row["알레르기목록"]:
                allergy_rows.append({
                    "학교명": row["학교명"],
                    "알레르기식품": allergy_item,
                })

        df_allergy = pd.DataFrame(allergy_rows)

        if df_allergy.empty:
            st.info("조회된 기간 내 알레르기 정보가 없습니다.")
        else:
            df_allergy_counts = (
                df_allergy.groupby(["알레르기식품", "학교명"])
                .size()
                .reset_index(name="출현횟수")
            )

            # Plotly 묶은 가로 막대그래프 생성
            fig_allergy = px.bar(
                df_allergy_counts,
                x="출현횟수",
                y="알레르기식품",
                color="학교명",
                orientation="h",
                barmode="group",
                title="알레르기 식품별 학교 간 양적 차이 비교",
                labels={"출현횟수": "출현 횟수(회)", "알레르기식품": "알레르기 유발 식품"},
                height=650,
            )
            # 출현 빈도가 높은 순서로 정렬
            fig_allergy.update_layout(
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="급식에 포함된 횟수 (회)",
                legend_title="학교명",
            )
            st.plotly_chart(fig_allergy, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 2: 시험기간 비타민 및 영양소 비교
    # ---------------------------------------------------------
    with tab2:
        st.subheader("학교별 비타민 및 피로회복 영양소 평균 제공량")
        st.caption("시험기간 피로 회복과 면역에 도움을 주는 주요 비타민과 미네랄(A, C, B1, B2, 칼슘, 철분)의 1회 급식 평균 제공량을 비교합니다.")

        nutrient_cols = [
            "비타민A(R.E)",
            "비타민C(mg)",
            "티아민(B1)",
            "리보플라빈(B2)",
            "칼슘(mg)",
            "철분(mg)",
        ]
        df_nut_avg = df.groupby("학교명")[nutrient_cols].mean().reset_index()

        # 세부 비타민 선택 기능
        selected_nut = st.selectbox("비교할 영양소를 선택하세요:", nutrient_cols)

        col_nut1, col_nut2 = st.columns(2)

        with col_nut1:
            fig_nut_bar = px.bar(
                df_nut_avg,
                x="학교명",
                y=selected_nut,
                color="학교명",
                text_auto=".1f",
                title=f"학교별 평균 {selected_nut} 제공량",
            )
            st.plotly_chart(fig_nut_bar, use_container_width=True)

        with col_nut2:
            # 전체 비타민/영양소 다중 비교 (Melted Bar Chart)
            df_nut_melted = pd.melt(
                df_nut_avg,
                id_vars=["학교명"],
                value_vars=["비타민C(mg)", "티아민(B1)", "리보플라빈(B2)", "철분(mg)"],
                var_name="영양소",
                value_name="평균제공량",
            )
            fig_nut_multi = px.bar(
                df_nut_melted,
                x="영양소",
                y="평균제공량",
                color="학교명",
                barmode="group",
                title="주요 비타민 및 미네랄 묶은 막대 비교",
            )
            st.plotly_chart(fig_nut_multi, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 3: 원본 데이터 확인
    # ---------------------------------------------------------
    with tab3:
        st.subheader("급식 식단 및 검출된 알레르기 상세 정보")
        display_df = df.copy()
        display_df["알레르기목록"] = display_df["알레르기목록"].apply(
            lambda x: ", ".join(x) if x else "없음"
        )
        st.dataframe(display_df, use_container_width=True)
