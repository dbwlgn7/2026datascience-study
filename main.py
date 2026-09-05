import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="서울 기온 데이터 종합 분석",
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

    # 날짜 데이터 정제
    df['날짜str'] = df[date_col].astype(str).str.strip()
    df['날짜dt'] = pd.to_datetime(df['날짜str'], errors='coerce')
    df['연도'] = df['날짜dt'].dt.year
    df['월'] = df['날짜dt'].dt.month

    # 기온 데이터 수치화 (결측치 처리)
    df['평균기온'] = pd.to_numeric(df[avg_col], errors='coerce')
    if min_col:
        df['최저기온'] = pd.to_numeric(df[min_col], errors='coerce')
    if max_col:
        df['최고기온'] = pd.to_numeric(df[max_col], errors='coerce')

    # 일교차 계산
    if '최저기온' in df.columns and '최고기온' in df.columns:
        df['일교차'] = df['최고기온'] - df['최저기온']

    # 계절 분류
    def get_season(month):
        if month in [3, 4, 5]:
            return '봄 (3~5월)'
        elif month in [6, 7, 8]:
            return '여름 (6~8월)'
        elif month in [9, 10, 11]:
            return '가을 (9~11월)'
        elif month in [12, 1, 2]:
            return '겨울 (12~2월)'
        return '기타'

    df['계절'] = df['월'].apply(get_season)

    # 일별 유효 데이터만 정제
    daily_df = df.dropna(subset=['연도', '평균기온', '최저기온', '최고기온']).copy()
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
    st.title("🌡️ 서울 기온 데이터 종합 시각화 대시보드")
    st.markdown(f"""
    기상청 서울 관측소 데이터(**{selected_years[0]}년 ~ {selected_years[1]}년**) 기반 기온 분포, 최저/최고기온 관계, 장기 변화 추이를 한눈에 확인해보세요.
    """)
    st.divider()

    # 탭 구성 (산점도 / 히스토그램 / 100년 추이)
    tab1, tab2, tab3 = st.tabs([
        "🔵 최저기온 vs 최고기온 산점도",
        "📊 일별 평균기온 히스토그램",
        "📈 연도별 기온 변화 추이"
    ])

    # [TAB 1] 최저기온 vs 최고기온 산점도
    with tab1:
        st.subheader("🌡️ 최저기온과 최고기온의 상관관계 (산점도)")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            color_by = st.selectbox(
                "색상 구분 기준",
                options=["계절", "월", "평균기온"],
                index=0
            )
        with c2:
            sample_size = st.slider(
                "샘플링 데이터 수 (속도 최적화)",
                min_value=1000,
                max_value=min(50000, len(filtered_daily)),
                value=min(10000, len(filtered_daily)),
                step=1000,
                help="데이터 양이 많을 경우 시각화 표현 및 조작 속도를 향상시키기 위해 무작위 표본 추출을 진행합니다."
            )

        # 표본 추출
        if len(filtered_daily) > sample_size:
            scatter_df = filtered_daily.sample(n=sample_size, random_state=42).copy()
        else:
            scatter_df = filtered_daily.copy()

        # 주요 요약 지표
        avg_range = filtered_daily['일교차'].mean()
        max_range_row = filtered_daily.loc[filtered_daily['일교차'].idxmax()]
        corr_val = filtered_daily['최저기온'].corr(filtered_daily['최고기온'])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("최저-최고 기온 상관계수", f"{corr_val:.3f}")
        m2.metric("평균 일교차", f"{avg_range:.1f} ℃")
        m3.metric("역대 최대 일교차", f"{max_range_row['일교차']:.1f} ℃", f"{max_range_row['날짜str']}")
        m4.metric("분석 표본 데이터 수", f"{len(scatter_df):,} / {len(filtered_daily):,} 일")

        # Plotly 산점도 생성
        if color_by == "계절":
            fig_scatter = px.scatter(
                scatter_df,
                x="최저기온",
                y="최고기온",
                color="계절",
                category_orders={"계절": ["봄 (3~5월)", "여름 (6~8월)", "가을 (9~11월)", "겨울 (12~2월)"]},
                color_discrete_map={
                    "봄 (3~5월)": "#4caf50",
                    "여름 (6~8월)": "#f44336",
                    "가을 (9~11월)": "#ff9800",
                    "겨울 (12~2월)": "#2196f3"
                },
                hover_data=["날짜str", "평균기온", "일교차"],
                opacity=0.6,
                title=f"서울 최저기온 vs 최고기온 (계절별 구분, {selected_years[0]}~{selected_years[1]}년)"
            )
        elif color_by == "월":
            fig_scatter = px.scatter(
                scatter_df,
                x="최저기온",
                y="최고기온",
                color="월",
                color_continuous_scale="Jet",
                hover_data=["날짜str", "평균기온", "일교차"],
                opacity=0.6,
                title=f"서울 최저기온 vs 최고기온 (월별 구분, {selected_years[0]}~{selected_years[1]}년)"
            )
        else:  # 평균기온
            fig_scatter = px.scatter(
                scatter_df,
                x="최저기온",
                y="최고기온",
                color="평균기온",
                color_continuous_scale="RdBu_r",
                hover_data=["날짜str", "일교차"],
                opacity=0.6,
                title=f"서울 최저기온 vs 최고기온 (평균기온별 구분, {selected_years[0]}~{selected_years[1]}년)"
            )

        # 45도 등가선 (y=x)
        min_val = min(scatter_df['최저기온'].min(), scatter_df['최고기온'].min())
        max_val = max(scatter_df['최저기온'].max(), scatter_df['최고기온'].max())
        
        fig_scatter.add_trace(go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode='lines',
            name='기온 동일선 (y=x)',
            line=dict(color='gray', dash='dash'),
            hoverinfo='skip'
        ))

        fig_scatter.update_layout(
            xaxis_title="일 최저기온 (℃)",
            yaxis_title="일 최고기온 (℃)",
            height=580
        )

        st.plotly_chart(fig_scatter, use_container_width=True)

        with st.expander("💡 산점도 보는 방법 및 해석 가이드"):
            st.markdown("""
            - **강한 양의 상관관계**: 최저기온이 높을수록 최고기온도 높아지는 경향을 보입니다. (상관계수 ≈ 0.98 이상)
            - **y=x 회색 점선과 거리가 멀수록**: 당일 **일교차(최고기온 - 최저기온)**가 큼을 의미합니다. (봄·가을철에 일교차가 커서 점선에서 멀리 떨어진 데이터가 많습니다)
            - **계절별 분포**: 
              - **겨울(파란색)**: 좌측 하단 (영하권 최저/최고기온)
              - **여름(빨간색)**: 우측 상단 (영상 20℃ 이상 최저기온, 30℃ 안팎 최고기온)
              - **봄/가을(초록/주황)**: 중앙부 넓게 분산 (대륙성 기후의 강한 일교차)
            """)

    # [TAB 2] 히스토그램
    with tab2:
        st.subheader("🌡️ 일별 평균기온 구간별 분포 (히스토그램)")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            bin_size = st.number_input("구간(Bin) 간격 (℃)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
        with c2:
            show_box = st.checkbox("상단 박스플롯(Boxplot) 표시", value=True)

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

        fig_hist = px.histogram(
            filtered_daily,
            x="평균기온",
            nbins=int((max_temp - min_temp) / bin_size),
            title=f"서울 일별 평균기온 분포 ({selected_years[0]}년~{selected_years[1]}년, 총 {total_days:,}일)",
            labels={"평균기온": "일별 평균기온 (℃)", "count": "일수 (Days)"},
            color_discrete_sequence=['#ff6b6b'],
            marginal="box" if show_box else None,
            opacity=0.8
        )

        fig_hist.update_traces(marker_line_color='white', marker_line_width=1)
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

    # [TAB 3] 100년 추이
    with tab3:
        st.subheader("📉 100년간 연평균 기온 변화 추이")
        
        show_ma = st.checkbox("10년 이동평균선 표시", value=True)
        show_trend = st.checkbox("선형 추세선 표시", value=True)

        fig_line = go.Figure()

        fig_line.add_trace(go.Scatter(
            x=filtered_yearly['연도'],
            y=filtered_yearly['연평균기온'],
            mode='lines+markers',
            name='연평균 기온',
            line=dict(color='#ff5722', width=1.5),
            marker=dict(size=4),
            hovertemplate='%{x}년: <b>%{y:.2f} ℃</b><extra></extra>'
        ))

        if show_ma:
            fig_line.add_trace(go.Scatter(
                x=filtered_yearly['연도'],
                y=filtered_yearly['10년이동평균'],
                mode='lines',
                name='10년 이동평균',
                line=dict(color='#2196f3', width=3),
                hovertemplate='%{x}년 (10년 평균): <b>%{y:.2f} ℃</b><extra></extra>'
            ))

        if show_trend and len(filtered_yearly) > 1:
            z = np.polyfit(filtered_yearly['연도'], filtered_yearly['연평균기온'], 1)
            p = np.poly1d(z)
            fig_line.add_trace(go.Scatter(
                x=filtered_yearly['연도'],
                y=p(filtered_yearly['연도']),
                mode='lines',
                name='장기 추세선',
                line=dict(color='#4caf50', width=2, dash='dash'),
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
