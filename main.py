import streamlit as st
import pandas as pd

# 브라우저 탭 및 앱 상단 설정
st.set_page_config(page_title="뇌졸중 예측 실습실", page_icon="🩺", layout="wide")

st.title("🩺 뇌졸중 예측 실습실")
st.markdown("---")

st.subheader("데이터 소개")

# 데이터 로드
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/stroke.csv"
    df = pd.read_csv(url, encoding="utf-8")
    return df

df = load_data()

# 1. 4개의 큰 숫자 카드 (지표)
col1, col2, col3, col4 = st.columns(4)

total_rows = len(df)
total_cols = len(df.columns)
stroke_patients = df['stroke'].sum()
stroke_ratio = (stroke_patients / total_rows) * 100

with col1:
    st.metric("전체 사람 수", f"{total_rows:,}명")
with col2:
    st.metric("데이터 열 개수", f"{total_cols}개")
with col3:
    st.metric("뇌졸중(stroke=1) 발생 수", f"{stroke_patients:,}명")
with col4:
    st.metric("뇌졸중 발생 비율", f"{stroke_ratio:.2f}%")

st.markdown("---")

# 2. 열 이름, 우리말 뜻, 값의 종류, 빈 값 개수 표
st.subheader("데이터 변수 설명표")

# 값의 종류 파악 로직
value_types = []
for col in df.columns:
    if df[col].nunique() <= 10:
        vals = ", ".join(df[col].dropna().unique().astype(str))
        value_types.append(f"범주형: {vals}")
    else:
        if pd.api.types.is_numeric_dtype(df[col]):
            value_types.append("수치형 (연속형 데이터)")
        else:
            value_types.append("문자형 데이터")

info_df = pd.DataFrame({
    "열 이름": df.columns,
    "우리말 뜻": ["" for _ in range(total_cols)], # 직접 채워 넣을 수 있게 빈칸 처리
    "값의 종류": value_types,
    "빈 값(결측치) 개수": df.isnull().sum().values
})

# 표 출력
st.dataframe(info_df, use_container_width=True)

st.markdown("---")

# 3. 데이터 처음 5줄
st.subheader("데이터 미리보기")
st.dataframe(df.head(5), use_container_width=True)

st.markdown("---")

# 4. 데이터 출처 (교재 보고 적을 자리)
st.subheader("데이터 출처")
st.info("교재를 참고하여 이곳에 데이터 출처를 적어보세요.")
