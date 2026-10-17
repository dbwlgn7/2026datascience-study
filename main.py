# main.py — 뇌졸중 예측 실습실: 이 데이터가 무엇인지 소개하는 첫 화면

import streamlit as st

st.set_page_config(
    page_title="뇌졸중 예측 실습실",
    page_icon="🩺",
    layout="wide"
)


def 홈_화면():
    # 기존 main.py의 데이터 읽기 및 화면 표시 코드를
    # 전부 이 함수 안에 넣으세요.
    import pandas as pd

    st.title("🩺 뇌졸중 예측 실습실")
    st.write(
        "건강 기록 5,110명분을 읽어 옵니다. "
        "왼쪽 메뉴에서 페이지를 넘기며 데이터를 탐색하고, "
        "모델을 만들고, 채점합니다."
    )

    데이터주소 = (
        "https://raw.githubusercontent.com/"
        "greatsong/modudata/main/data/stroke.csv"
    )

    @st.cache_data
    def 데이터_읽기():
        return pd.read_csv(데이터주소, encoding="utf-8")

    df = 데이터_읽기()

    칸1, 칸2, 칸3, 칸4 = st.columns(4)
    칸1.metric("전체 사람 수", f"{len(df):,}명")
    칸2.metric("열 개수", f"{df.shape[1]}개")
    칸3.metric("뇌졸중을 겪은 사람", f"{int(df['stroke'].sum()):,}명")
    칸4.metric("그 비율", f"{df['stroke'].mean() * 100:.2f}%")


페이지 = st.navigation([
    st.Page(홈_화면, title="실습실 홈", icon="🏠", default=True),
    st.Page("pages/1_탐색.py", title="1. 데이터 탐색", icon="🔎"),
    st.Page("pages/2_분류_모델.py", title="2. 분류 모델", icon="🔎"),
    st.Page("pages/3_채점표.py", title="3. 채점표", icon="🔎"),
    st.Page("pages/4_전처리.py", title="3. 전처리", icon="🔎"),
])

페이지.run()
