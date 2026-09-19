import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="서울 기온 예측기",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ 서울 연평균 기온 예측기")
st.write("서울 기온 데이터를 바탕으로 1908년 이후 지난 연수를 독립변수로 한 선형 회귀 분석 결과입니다.")

# 데이터 불러오기 및 전처리
@st.cache_data
def load_and_preprocess_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/bb860932644270ad1199f10d3e7670e30231bce4/data/seoul.csv"
    
    # UTF-8 인코딩으로 CSV 읽기
    df = pd.read_csv(url, encoding="utf-8")
    
    # 날짜 컬럼 datetime 변환 및 연도 추출
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    
    # 평균기온 결측치 제거
    df_clean = df.dropna(subset=["평균기온"])
    
    # 연도별 관측일수 및 평균기온 계산
    yearly = df_clean.groupby("연도").agg(
        관측일수=("평균기온", "count"),
        연평균기온=("평균기온", "mean")
    ).reset_index()
    
    # 조건 필터링: 2025년 이하 & 관측일수 300일 이상
    filtered = yearly[(yearly["연도"] <= 2025) & (yearly["관측일수"] >= 300)].copy()
    
    return filtered

try:
    data = load_and_preprocess_data()
    
    # 메타 정보 계산
    num_years = len(data)
    start_year = int(data["연도"].min())
    end_year = int(data["연도"].max())
    
    # 독립변수 X: 1908년부터 지난 연수 (연도 - 1908)
    # 종속변수 Y: 연평균기온
    X = data["연도"] - 1908
    Y = data["연평균기온"]
    
    # 선형 회귀분석 및 상관계수 계산
    slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)
    
    # 화면 상단 주요 정보 표시
    st.subheader("📌 회귀 직선 데이터 정보")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("학습된 해의 개수", f"{num_years}개 연도")
    col2.metric("시작 연도", f"{start_year}년")
    col3.metric("끝 연도", f"{end_year}년")
    col4.metric("상관계수 (r)", f"{r_value:.4f}")
    
    st.divider()
    
    # 연도 선택 슬라이더 (1900 ~ 2100)
    st.subheader("🔮 예상 기온 확인하기")
    selected_year = st.slider(
        "예측하고 싶은 연도를 선택하세요",
        min_value=1900,
        max_value=2100,
        value=2025,
        step=1
    )
    
    # 선택된 연도의 예상 기온 계산
    selected_x = selected_year - 1908
    predicted_temp = slope * selected_x + intercept
    
    # 예상 기온 강조 표시
    st.metric(
        label=f"🌡️ {selected_year}년 서울 예상 연평균 기온",
        value=f"{predicted_temp:.2f} °C"
    )
    
    # Plotly 시각화
    st.subheader("📊 연도별 평균기온 산점도 및 회귀 직선")
    
    # 회귀선 그리기용 연도 범위 (1900년~2100년)
    years_line = np.arange(1900, 2101)
    x_line = years_line - 1908
    y_line = slope * x_line + intercept
    
    fig = go.Figure()
    
    # 1. 실제 관측 데이터 산점도
    fig.add_trace(
        go.Scatter(
            x=data["연도"],
            y=data["연평균기온"],
            mode="markers",
            name="실제 관측 데이터",
            marker=dict(color="#1f77b4", size=7, opacity=0.8),
            hovertemplate="연도: %{x}년<br>평균기온: %{y:.2f}°C<extra></extra>"
        )
    )
    
    # 2. 회귀 직선
    fig.add_trace(
        go.Scatter(
            x=years_line,
            y=y_line,
            mode="lines",
            name="회귀 직선",
            line=dict(color="#ff7f0e", width=2, dash="dash"),
            hovertemplate="연도: %{x}년<br>회귀 예측값: %{y:.2f}°C<extra></extra>"
        )
    )
    
    # 3. 슬라이더로 선택된 연도 강조 표시
    fig.add_trace(
        go.Scatter(
            x=[selected_year],
            y=[predicted_temp],
            mode="markers",
            name=f"선택 연도({selected_year}년)",
            marker=dict(color="red", size=14, symbol="star", line=dict(color="black", width=1)),
            hovertemplate=f"선택 연도: {selected_year}년<br>예상 기온: {predicted_temp:.2f}°C<extra></extra>"
        )
    )
    
    # 레이아웃 설정
    fig.update_layout(
        xaxis_title="연도",
        yaxis_title="평균기온 (°C)",
        xaxis=dict(range=[1895, 2105], dtick=20),
        template="plotly_white",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 로드하는 중 오류가 발생했습니다: {e}")
