import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="서울 100년 기온 변화 분석",
    page_icon="🌡️",
    layout="wide"
)

# 2. 데이터 로드 및 전처리 함수 (캐싱 적용)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
    
    # 인코딩 호환성을 위한 처리
    df = None
    for enc in ['cp949', 'utf-8-sig', 'utf-8', 'euc-kr']:
        try:
            df = pd.read_csv(url, encoding=enc)
            break
        except Exception:
            continue
            
    if df is None:
        st.error("데이터를 불러오는데 실패했습니다.")
        return None, None

    # 컬럼명 공백 제거
    df.columns = df.columns.str.strip()
    
    # 주요 컬럼 탐색
    date_col = [c for c in df.columns if '날짜' in c][0]
    avg_col = [c for c in df.columns if '평균' in c][0]

    # 날짜 데이터 정제 및 연도 추출
    df[date_col] = df[date_col].astype(str).str.strip()
    df['연도'] = df[date_col].str.extract(r'(\d{4})').astype(float)
    
    # 기온 데이터 수치화
    df['평균기온'] = pd.to_numeric(df[avg_col], errors='coerce')

    # 연도별 평균 산출
    yearly = df.groupby('연도').agg(
        연평균기온=('평균기온', 'mean'),
        관측일수=('평균기온', 'count')
    ).reset_index()

    # 관측일수가 유효한 연도만 필터링 (최소 300일 이상)
    yearly = yearly[yearly['관측일수'] >= 300].copy()
    yearly['연도'] = yearly['연도'].astype(int)
    
    # 10년 이동평균 계산
    yearly['10년이동평균'] = yearly['연평균기온'].rolling(window=10, min_periods=5).mean()

    return yearly, df

# 데이터 로드
yearly_df, raw_df = load_data()

if yearly_df is not None:
    # 3. 사이드바 - 분석 옵션 컨트롤
    st.sidebar.header("⚙️ 분석 설정")
    
    min_year = int(yearly_df['연도'].min())
    max_year = int(yearly_df['연도'].max())
    
    selected_years = st.sidebar.slider(
        "조회 연도 범위 선택",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )
    
    show_ma = st.sidebar.checkbox("10년 이동평균선 표시", value=True)
    show_trend = st.sidebar.checkbox("선형 추세선 표시", value=True)

    # 선택된 범위 데이터 필터링
    filtered_df = yearly_df[(yearly_df['연도'] >= selected_years[0]) & (yearly_df['연도'] <= selected_years[1])]

    # 4. 메인 화면 헤더
    st.title("🌡️ 서울의 지난 100년 연평균 기온 변화")
    st.markdown("""
    기상청 서울 관측소 데이터(1907년~)를 바탕으로 **지난 100여 년간 서울의 연평균 기온 상승 경향**을 분석한 대시보드입니다.
    """)
    st.divider()

    # 5. 핵심 지표 요약 (Key Metrics)
    col1, col2, col3, col4 = st.columns(4)
    
    start_avg = filtered_df.iloc[:10]['연평균기온'].mean() if len(filtered_df) >= 10 else filtered_df['연평균기온'].mean()
    end_avg = filtered_df.iloc[-10:]['연평균기온'].mean() if len(filtered_df) >= 10 else filtered_df['연평균기온'].mean()
    diff = end_avg - start_avg
    
    hottest_row = filtered_df.loc[filtered_df['연평균기온'].idxmax()]
    coolest_row = filtered_df.loc[filtered_df['연평균기온'].idxmin()]

    with col1:
        st.metric("조회 기간", f"{selected_years[0]}년 ~ {selected_years[1]}년")
    with col2:
        st.metric("가장 뜨거웠던 해", f"{int(hottest_row['연도'])}년", f"{hottest_row['연평균기온']:.1f} ℃")
    with col3:
        st.metric("가장 추웠던 해", f"{int(coolest_row['연도'])}년", f"{coolest_row['연평균기온']:.1f} ℃")
    with col4:
        st.metric("기간 내 기온 변화 (초기10년 대비)", f"{diff:+.2f} ℃", delta_color="inverse" if diff > 0 else "normal")

    st.subheader("📉 연도별 연평균 기온 추이 그래프")

    # 6. Plotly 그래프 생성
    fig = go.Figure()

    # 연평균 기온 라인
    fig.add_trace(go.Scatter(
        x=filtered_df['연도'],
        y=filtered_df['연평균기온'],
        mode='lines+markers',
        name='연평균 기온',
        line=dict(color='#FF5722', width=1.5),
        marker=dict(size=4),
        hovertemplate='%{x}년: <b>%{y:.2f} ℃</b><extra></extra>'
    ))

    # 10년 이동평균선
    if show_ma:
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=filtered_df['10년이동평균'],
            mode='lines',
            name='10년 이동평균',
            line=dict(color='#2196F3', width=3),
            hovertemplate='%{x}년 (10년 평균): <b>%{y:.2f} ℃</b><extra></extra>'
        ))

    # 추세선 (Linear Trendline)
    if show_trend and len(filtered_df) > 1:
        z = np.polyfit(filtered_df['연도'], filtered_df['연평균기온'], 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=p(filtered_df['연도']),
            mode='lines',
            name='장기 추세선',
            line=dict(color='#4CAF50', width=2, dash='dash'),
            hoverinfo='skip'
        ))

    # 레이아웃 스타일 설정
    fig.update_layout(
        xaxis_title="연도 (Year)",
        yaxis_title="연평균 기온 (℃)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # 7. 데이터 보기 및 설명
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.expander("💡 그래프 보는 방법"):
            st.markdown("""
            - **주황색 실선**: 해당 연도의 1년 평균 기온입니다.
            - **파란색 두꺼운 선**: 단기 변동을 줄이고 기후적 흐름을 보여주는 **10년 이동평균**입니다.
            - **초록색 점선**: 전체 기간 동안 기온이 지속적으로 상승하고 있음을 보여주는 **장기 추세선**입니다.
            """)

    with col_right:
        with st.expander("📋 연도별 데이터 표 보기"):
            display_df = filtered_df[['연도', '연평균기온', '10년이동평균']].copy()
            display_df.columns = ['연도', '연평균 기온 (℃)', '10년 이동평균 (℃)']
            st.dataframe(display_df.sort_values(by='연도', ascending=False), height=200, use_container_width=True)
