import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="서울 기온 데이터 분석 - 히스토그램 및 추이",
    page_icon="🌡️",
    layout="wide"
)

# 2. 데이터 로드 및 전처리 함수 (캐싱 적용)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
    
    # 인코딩 호환성을 위한 예외 처리
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
    min_col = [c for c in df.columns if '최저' in c][0] if any('최저' in c for c in df.columns) else None
    max_col = [c for c in df.columns if '최고' in c][0] if any('최고' in c for c in df.columns) else None

    # 날짜 데이터 정제 및 연도 추출
    df[date_col] = df[date_col].astype(str).str.strip()
    df['연도'] = df[date_col].str.extract(r'(\d{4})').astype(float)
    
    # 기온 데이터 수치화 (결측치 처리)
    df['평균기온'] = pd.to_numeric(df[avg_col], errors='coerce')
    if min_col:
        df['최저기온'] = pd.to_numeric(df[min_col], errors='coerce')
    if max_col:
        df['최고기온'] = pd.to_numeric(df[max_col], errors='coerce')

    # 일별 유효 데이터만 정제
    daily_df = df.dropna(subset=['연도', '평균기온']).copy()
    daily_df['연도'] = daily_df['연도'].astype(int)

    # 연도별 평균 산출
    yearly_df = daily_df.groupby('연도').agg(
        연평균기온=('평균기온', 'mean'),
        관측일수=('평균기온', 'count')
    ).reset_index()

    # 관측일수 300일 이상 연도만 포함
    yearly_df = yearly_df[yearly_df['관측일수'] >= 300].copy()
    yearly_df['10년이동평균'] = yearly_df['연평균기온'].rolling(window=10, min_periods=5).mean()

    return daily_df, yearly_df

# 데이터 로드
daily_df, yearly_df = load_data()

if daily_df is not None and yearly_df is not None:
    # 3. 사이드바 - 설정 컨트롤
    st.sidebar.header("⚙️ 분석 설정")
    
    min_year = int(daily_df['연도'].min())
    max_year = int(daily_df['연도'].max())
    
    selected_years = st.sidebar.slider(
        "조회 연도 범위 선택",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # 선택된 연도 범위 데이터 필터링
    filtered_daily = daily_df[(daily_df['연도'] >= selected_years[0]) & (daily_df['연도'] <= selected_years[1])]
    filtered_yearly = yearly_df[(yearly_df['연도'] >= selected_years[0]) & (yearly_df['연도'] <= selected_years[1])]

    # 4. 메인 화면 헤더
    st.title("📊 서울 일별 평균기온 분포 및 100년 변천사")
    st.markdown(f"""
    기상청 서울 관측소 데이터(**{selected_years[0]}년 ~ {selected_years[1]}년**) 기반의 기온 분포 및 장기 추이 분석 대시보드입니다.
    """)
    st.divider()

    # 탭 구성 (히스토그램 분석 / 100년 추이 분석)
    tab1, tab2 = st.tabs(["📊 일별 평균기온 히스토그램", "📈 연도별 기온 변화 추이"])

    with tab1:
        st.subheader("🌡️ 일별 평균기온 구간별 분포 (히스토그램)")
        
        # 히스토그램 옵션 조절
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            bin_size = st.number_input("구간(Bin) 간격 (℃)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
        with c2:
            show_box = st.checkbox("상단 박스플롯(Boxplot) 표시", value=True)

        # 주요 요약 통계
        mean_temp = filtered_daily['평균기온'].mean()
        median_temp = filtered_daily['평균기온'].median()
        min_temp = filtered_daily['평균기온'].min()
        max_temp = filtered_daily['평균기온'].max()
        total_days = len(filtered_daily)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("총 관측 일수", f"{total_days:,} 일")
        m2.metric("전체 일평균기온 평균", f"{mean_temp:.1f} ℃")
        m3.metric("중앙값", f"{median_temp:.1f} ℃")
        m4.metric("역대 최저 일평균", f"{min_temp:.1f} ℃")
        m5.metric("역대 최고 일평균", f"{max_temp:.1f} ℃")

        # Plotly 히스토그램 생성
        fig_hist = px.histogram(
            filtered_daily,
            x="평균기온",
            nbins=int((max_temp - min_temp) / bin_size),
            title=f"서울 일별 평균기온 분포 ({selected_years[0]}년~{selected_years[1]}년, 총 {total_days:,}일)",
            labels={"평균기온": "일별 평균기온 (℃)", "count": "일수 (Days)"},
            color_discrete_sequence=['#FF6B6B'],
            marginal="box" if show_box else None,
            opacity=0.8
        )

        fig_hist.update_traces(marker_line_color='white', marker_line_width=1)
        
        # 기준선 추가
        fig_hist.add_vline(x=mean_temp, line_dash="dash", line_color="blue", annotation_text=f"평균: {mean_temp:.1f}℃", annotation_position="top left")
        fig_hist.add_vline(x=0, line_dash="dot", line_color="gray", annotation_text="0℃ (영하/영상)", annotation_position="bottom left")

        fig_hist.update_layout(
            xaxis_title="일별 평균기온 (℃)",
            yaxis_title="날짜 수 (일)",
            bargap=0.05,
            height=520,
            hovermode="x unified"
        )

        st.plotly_chart(fig_hist, use_container_width=True)

        # 구간별 해석 가이드
        with st.expander("💡 히스토그램 해석 및 구간별 특징"):
            sub_zero_days = (filtered_daily['평균기온'] < 0).sum()
            sub_zero_ratio = (filtered_daily['평균기온'] < 0).mean() * 100
            hot_days = (filtered_daily['평균기온'] >= 25).sum()
            hot_ratio = (filtered_daily['평균기온'] >= 25).mean() * 100

            st.markdown(f"""
            - **쌍봉형(Bimodal) 분포**: 서울의 기온 분포는 계절성(사계절)으로 인해 여름철 고온 구간(20℃~25℃)과 봄·가을/겨울 구간에 두 개의 봉우리가 나타납니다.
            - **영하권(0℃ 미만) 일수**: 전체 {total_days:,}일 중 일평균기온이 영하인 날은 **{sub_zero_ratio:.1f}%** ({sub_zero_days:,}일) 입니다.
            - **고온권(25℃ 이상) 일수**: 일평균기온이 25℃ 이상인 날은 **{hot_ratio:.1f}%** ({hot_days:,}일) 입니다.
            """)

    with tab2:
        st.subheader("📉 100년간 연평균 기온 변화 추이")
        
        show_ma = st.checkbox("10년 이동평균선 표시", value=True)
        show_trend = st.checkbox("선형 추세선 표시", value=True)

        fig_line = go.Figure()

        # 연평균 기온
        fig_line.add_trace(go.Scatter(
            x=filtered_yearly['연도'],
            y=filtered_yearly['연평균기온'],
            mode='lines+markers',
            name='연평균 기온',
            line=dict(color='#FF5722', width=1.5),
            marker=dict(size=4),
            hovertemplate='%{x}년: <b>%{y:.2f} ℃</b><extra></extra>'
        ))

        # 10년 이동평균
        if show_ma:
            fig_line.add_trace(go.Scatter(
                x=filtered_yearly['연도'],
                y=filtered_yearly['10년이동평균'],
                mode='lines',
                name='10년 이동평균',
                line=dict(color='#2196F3', width=3),
                hovertemplate='%{x}년 (10년 평균): <b>%{y:.2f} ℃</b><extra></extra>'
            ))

        # 추세선
        if show_trend and len(filtered_yearly) > 1:
            z = np.polyfit(filtered_yearly['연도'], filtered_yearly['연평균기온'], 1)
            p = np.poly1d(z)
            fig_line.add_trace(go.Scatter(
                x=filtered_yearly['연도'],
                y=p(filtered_yearly['연도']),
                mode='lines',
                name='장기 추세선',
                line=dict(color='#4CAF50', width=2, dash='dash'),
                hoverinfo='skip'
            ))

        fig_line.update_layout(
            xaxis_title="연도 (Year)",
            yaxis_title="연평균 기온 (℃)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            height=500
        )

        st.plotly_chart(fig_line, use_container_width=True)
