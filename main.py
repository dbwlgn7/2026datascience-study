import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 스트림릿 페이지 설정
st.set_page_config(
    page_title="서울 기온 예측기",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ 서울 연평균 기온 예측기")
st.write("서울 기온 데이터를 바탕으로 기온 상승 추세를 분석하고 미래 기온을 예측합니다.")

# 데이터 불러오기 및 전처리 함수
@st.cache_data
def load_and_preprocess_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/bb860932644270ad1199f10d3e7670e30231bce4/data/seoul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # 날짜 변환 및 연도 추출
    df['날짜'] = pd.to_datetime(df['날짜'])
    df['연도'] = df['날짜'].dt.year
    
    # 연도별 평균기온 및 관측일수 집계
    yearly_df = df.groupby('연도').agg(
        평균기온=('평균기온', 'mean'),
        관측일수=('평균기온', 'count')
    ).reset_index()
    
    # 조건 필터링: 2025년 이하 & 관측일수 300일 이상
    filtered_df = yearly_df[(yearly_df['연도'] <= 2025) & (yearly_df['관측일수'] >= 300)].copy()
    
    # 1908년부터 지난 연수를 독립 변수 X로 생성
    filtered_df['X'] = filtered_df['연도'] - 1908
    
    return filtered_df

try:
    df_filtered = load_and_preprocess_data()

    # 기본 통계치
    start_year = int(df_filtered['연도'].min())
    end_year = int(df_filtered['연도'].max())
    total_count = len(df_filtered)

    # 1. 전체 기간 회귀 분석 (1908년 기준 X 사용)
    X_all = df_filtered['X']
    Y_all = df_filtered['평균기온']
    slope_all, intercept_all = np.polyfit(X_all, Y_all, 1)
    corr_all = np.corrcoef(X_all, Y_all)[0, 1]
    slope_100_all = slope_all * 100  # 100년당 기온 변화량

    # 2. 최근 20년 회귀 분석
    recent_20_start = end_year - 19
    df_recent = df_filtered[df_filtered['연도'] >= recent_20_start].copy()
    recent_count = len(df_recent)
    recent_start_act = int(df_recent['연도'].min())
    recent_end_act = int(df_recent['연도'].max())

    X_recent = df_recent['X']
    Y_recent = df_recent['평균기온']
    slope_recent, intercept_recent = np.polyfit(X_recent, Y_recent, 1)
    slope_100_recent = slope_recent * 100  # 100년당 기온 변화량

    # 사이드바: 데이터 요약 정보
    st.sidebar.header("📊 데이터 개요")
    st.sidebar.info(f"""
    - **분석에 사용된 해의 개수**: {total_count}개
    - **시작 연도**: {start_year}년
    - **끝 연도**: {end_year}년
    - **전체 기간 상관계수**: {corr_all:.4f}
    """)

    # --- Section 1: 100년당 기온 상승률 비교 ---
    st.subheader("🔥 기온 상승 속도 비교 (100년당 변화량)")
    col_metric1, col_metric2 = st.columns(2)

    with col_metric1:
        st.metric(
            label=f"🌐 전체 기간 ({start_year}~{end_year}년 / {total_count}개 연도)",
            value=f"{slope_100_all:+.2f} °C / 100년",
            delta=f"연간 {slope_all:+.4f} °C"
        )

    with col_metric2:
        st.metric(
            label=f"⚡ 최근 20년 ({recent_start_act}~{recent_end_act}년 / {recent_count}개 연도)",
            value=f"{slope_100_recent:+.2f} °C / 100년",
            delta=f"전체 대비 {slope_100_recent - slope_100_all:+.2f} °C (100년 기준)",
            delta_color="normal"
        )

    st.markdown("---")

    # --- Section 2: 연도 선택 및 예측 ---
    st.subheader("🔮 예측 연도 선택")
    selected_year = st.slider(
        "슬라이더를 움직여 예측할 연도를 선택하세요 (1900년 ~ 2100년)",
        min_value=1900,
        max_value=2100,
        value=2025,
        step=1
    )

    # 선택한 연도의 X 값 계산 (1908년 기준)
    pred_x = selected_year - 1908
    pred_temp_all = slope_all * pred_x + intercept_all
    pred_temp_recent = slope_recent * pred_x + intercept_recent

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.metric(
            label=f"📍 {selected_year}년 예상 평균기온 (전체 추세 기준)",
            value=f"{pred_temp_all:.2f} °C"
        )
    with p_col2:
        st.metric(
            label=f"📍 {selected_year}년 예상 평균기온 (최근 20년 추세 기준)",
            value=f"{pred_temp_recent:.2f} °C",
            delta=f"전체 추세 대비 {pred_temp_recent - pred_temp_all:+.2f} °C"
        )

    st.markdown("---")

    # --- Section 3: Plotly 시각화 ---
    st.subheader("📈 연평균 기온 산점도 및 회귀선")

    # 회귀선 x축 범위 설정 (시작 연도 ~ 2100년까지 연도 그대로 표현)
    line_years_all = np.arange(start_year, 2101)
    line_x_all = line_years_all - 1908
    line_y_all = slope_all * line_x_all + intercept_all

    line_years_recent = np.arange(recent_start_act, 2101)
    line_x_recent = line_years_recent - 1908
    line_y_recent = slope_recent * line_x_recent + intercept_recent

    fig = go.Figure()

    # 실제 데이터 산점도
    fig.add_trace(go.Scatter(
        x=df_filtered['연도'],
        y=df_filtered['평균기온'],
        mode='markers',
        name='실제 연평균기온',
        marker=dict(color='royalblue', size=7, opacity=0.75)
    ))

    # 전체 기간 회귀선
    fig.add_trace(go.Scatter(
        x=line_years_all,
        y=line_y_all,
        mode='lines',
        name=f'전체 회귀선 (100년당 {slope_100_all:+.2f}°C)',
        line=dict(color='firebrick', width=2.5)
    ))

    # 최근 20년 회귀선
    fig.add_trace(go.Scatter(
        x=line_years_recent,
        y=line_y_recent,
        mode='lines',
        name=f'최근 20년 회귀선 (100년당 {slope_100_recent:+.2f}°C)',
        line=dict(color='darkorange', width=2.5, dash='dash')
    ))

    # 선택된 연도 강조 표시
    fig.add_trace(go.Scatter(
        x=[selected_year],
        y=[pred_temp_all],
        mode='markers+text',
        name=f'선택한 해({selected_year}년예측)',
        text=[f"{pred_temp_all:.2f}°C"],
        textposition="top center",
        marker=dict(color='red', size=12, symbol='star')
    ))

    fig.update_layout(
        xaxis_title="연도",
        yaxis_title="평균기온 (°C)",
        xaxis=dict(tickformat="d"),
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 데이터 요약 카드 하단 표시
    st.info(f"💡 **분석 결과 정보**: 총 **{total_count}개**의 연도 데이터를 사용했습니다. (기간: {start_year}년 ~ {end_year}년)")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
