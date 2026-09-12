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

st.title("🥗 전국 학교 급식 알레르기 & 영양소 분석 대시보드")
st.caption(
    "선택한 학교들의 알레르기 유발 식품 및 비타민 제공량을 직관적으로 비교하고, 특정 날짜의 상세 식단을 조회합니다."
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
# 2. 사이드바 - 학교 검색 및 조회 기간 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 학교 검색 & 기간 설정")

school_input_1 = st.sidebar.text_input("첫 번째 학교명", "인천남동고등학교")
school_input_2 = st.sidebar.text_input("두 번째 학교명", "동인천고등학교")
school_input_3 = st.sidebar.text_input("세 번째 학교명", "석정여자고등학교")

start_date = st.sidebar.text_input("조회 시작일 (YYYYMMDD)", "20260901")
end_date = st.sidebar.text_input("조회 종료일 (YYYYMMDD)", "20260915")
api_key = st.sidebar.text_input("NEIS API Key (선택)", type="password")


# ---------------------------------------------------------
# 3. 데이터 수집 및 파싱 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def search_school_info(school_name, key=None):
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
    return [re.sub(r"\([0-9\.]+\)", "", d).strip() for d in raw_dishes if d]


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
# 4. 데이터 로드
# ---------------------------------------------------------
user_school_inputs = [school_input_1, school_input_2, school_input_3]
target_schools_info = []

with st.spinner("급식 데이터를 수집 중입니다..."):
    for s_input in user_school_inputs:
        if s_input.strip():
            info = search_school_info(s_input, api_key)
            if info:
                target_schools_info.append(info)

    all_data = []
    for s_info in target_schools_info:
        meals = fetch_meal_data(
            s_info["ofcdc"], s_info["code"], start_date, end_date, api_key
        )
        for m in meals:
            dish_list = clean_dish_names(m["DDISH_NM"])
            cal_match = re.search(r"[\d\.]+", m.get("CAL_INFO", "0"))
            cal_val = float(cal_match.group()) if cal_match else 0.0

            record = {
                "학교명": s_info["name"],
                "급식일": m["MLSV_YMD"],
                "메뉴목록": dish_list,
                "메뉴": ", ".join(dish_list),
                "알레르기목록": parse_allergies(m["DDISH_NM"]),
                "칼로리(kcal)": cal_val,
            }
            record.update(parse_nutrition(m.get("NTR_INFO", "")))
            all_data.append(record)

df = pd.DataFrame(all_data)

# ---------------------------------------------------------
# 5. 대시보드 화면 구성
# ---------------------------------------------------------
if df.empty:
    st.info("💡 사이드바에서 비교하고 싶은 학교명을 입력해 주세요.")
else:
    df["급식일"] = pd.to_datetime(df["급식일"], format="%Y%m%d")

    # 상단 요약 카드
    col1, col2, col3 = st.columns(3)
    col1.metric("조회된 학교 수", f"{len(df['학교명'].unique())}개교")
    col2.metric("수집된 총 식단 수", f"{len(df)}건")
    col3.metric("알레르기 감지 총 횟수", f"{sum(len(a) for a in df['알레르기목록'])}회")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 알레르기 식품 빈도 (가독성 최적화)",
        "🍋 시험기간 영양소 비교",
        "📅 특정 날짜 급식 상세 조회",
        "📋 데이터 전체 보기",
    ])

    # ---------------------------------------------------------
    # Tab 1: 보기 옵션을 갖춘 고가독성 알레르기 그래프
    # ---------------------------------------------------------
    with tab1:
        st.subheader("학교별 알레르기 유발 식품 출현 빈도 비교")

        allergy_rows = []
        for _, row in df.iterrows():
            for a in row["알레르기목록"]:
                allergy_rows.append({"학교명": row["학교명"], "알레르기식품": a})

        df_allergy = pd.DataFrame(allergy_rows)

        if df_allergy.empty:
            st.info("해당 기간 내 감지된 알레르기 정보가 없습니다.")
        else:
            # 1. 보기 옵션 필터 추가 (복잡도 해결)
            col_filter1, col_filter2 = st.columns([2, 1])

            with col_filter1:
                view_mode = st.radio(
                    "👀 그래프 보기 모드 선택:",
                    [
                        "🔥 가장 자주 나오는 TOP 5 식품만 보기",
                        "🎯 특정 알레르기 식품 1개 선택 비교",
                        "📜 전체 식품 보기 (넓은 간격)",
                    ],
                    horizontal=True,
                )

            # 데이터 그룹화
            df_counts = (
                df_allergy.groupby(["알레르기식품", "학교명"])
                .size()
                .reset_index(name="출현횟수")
            )

            # 모드별 데이터 필터링
            if "TOP 5" in view_mode:
                top_items = (
                    df_counts.groupby("알레르기식품")["출현횟수"]
                    .sum()
                    .nlargest(5)
                    .index
                )
                df_counts = df_counts[df_counts["알레르기식품"].isin(top_items)]

            elif "1개 선택" in view_mode:
                all_unique_items = sorted(df_counts["알레르기식품"].unique())
                with col_filter2:
                    selected_item = st.selectbox(
                        "조회할 알레르기 식품:", all_unique_items
                    )
                df_counts = df_counts[df_counts["알레르기식품"] == selected_item]

            # 2. 동적 높이 및 여백 계산 (막대가 붙는 현상 완벽 방지)
            unique_items_count = df_counts["알레르기식품"].nunique()
            chart_height = max(400, unique_items_count * 75)  # 1항목당 75px로 넉넉하게 배치

            max_val = df_counts["출현횟수"].max() if not df_counts.empty else 5

            # Plotly 가독성 극대화 차트 생성
            fig_h_bar = px.bar(
                df_counts,
                x="출현횟수",
                y="알레르기식품",
                color="학교명",
                orientation="h",
                barmode="group",
                text="출현횟수",
                title=f"<b>[알레르기 식품 비교]</b> {view_mode}",
                labels={"출현횟수": "출현 횟수(회)", "알레르기식품": "알레르기 식품"},
                height=chart_height,
                template="plotly_dark",
            )

            # 막대 사이 여백(bargap) 및 텍스트 위치 가독성 최적화
            fig_h_bar.update_traces(
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=14, color="white"),
                marker=dict(line=dict(width=1, color="rgba(255, 255, 255, 0.3)")),  # 막대 경계선 추가
            )

            fig_h_bar.update_layout(
                yaxis={"categoryorder": "total ascending", "tickfont": dict(size=14)},
                xaxis=dict(
                    range=[0, max_val * 1.25],  # 오른쪽에 25% 여유 공간 확보하여 수치 잘림 방지
                    dtick=1,
                    title_font=dict(size=14),
                ),
                font=dict(size=13),
                bargap=0.45,       # 그룹 간 넓은 여백 (위아래 겹침 방지)
                bargroupgap=0.15,  # 같은 그룹 막대 간 여백
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=13),
                ),
                margin=dict(l=30, r=80, t=60, b=40),
            )

            st.plotly_chart(fig_h_bar, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 2: 영양소 비교 그래프
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
            text="평균제공량",
            title="<b>[시험기간 피로회복 영양소 평균 제공량]</b>",
            template="plotly_dark",
            height=500,
        )
        fig_nut.update_traces(
            texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False
        )
        fig_nut.update_layout(
            font=dict(size=13),
            bargap=0.3,
            bargroupgap=0.1,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        st.plotly_chart(fig_nut, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 3: 특정 날짜 급식 상세 조회
    # ---------------------------------------------------------
    with tab3:
        st.subheader("🔍 일별 급식 메뉴 & 알레르기 상세 조회")
        st.caption("학교와 날짜를 선택하면 해당 날짜의 전체 메뉴와 알레르기 정보를 보여줍니다.")

        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            selected_school = st.selectbox(
                "조회할 학교를 선택하세요", options=df["학교명"].unique()
            )

        school_dates = (
            df[df["학교명"] == selected_school]["급식일"]
            .dt.strftime("%Y-%m-%d")
            .unique()
        )

        with col_sel2:
            selected_date_str = st.selectbox(
                "조회할 날짜를 선택하세요", options=school_dates
            )

        selected_meal = df[
            (df["학교명"] == selected_school)
            & (df["급식일"].dt.strftime("%Y-%m-%d") == selected_date_str)
        ]

        if not selected_meal.empty:
            meal_data = selected_meal.iloc[0]

            st.markdown("---")
            st.success(f"📌 **{selected_school}** ({selected_date_str} 중식)")

            col_m1, col_m2, col_m3 = st.columns([2, 2, 1])

            with col_m1:
                st.markdown("### 🍱 오늘의 메뉴")
                for item in meal_data["메뉴목록"]:
                    st.write(f"- **{item}**")

            with col_m2:
                st.markdown("### ⚠️ 포함된 알레르기 성분")
                if meal_data["알레르기목록"]:
                    for alg in meal_data["알레르기목록"]:
                        st.warning(f"• {alg}")
                else:
                    st.info("표시된 알레르기 성분이 없습니다.")

            with col_m3:
                st.markdown("### 📊 영양 정보")
                st.metric("총 칼로리", f"{meal_data['칼로리(kcal)']:.0f} kcal")
                st.metric("비타민C", f"{meal_data['비타민C(mg)']:.1f} mg")
                st.metric("티아민(B1)", f"{meal_data['티아민(B1)']:.2f} mg")

    # ---------------------------------------------------------
    # Tab 4: 데이터 전체 보기
    # ---------------------------------------------------------
    with tab4:
        st.subheader("수집된 데이터 전체 표")
        st.dataframe(df, use_container_width=True)
