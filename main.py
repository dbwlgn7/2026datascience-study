import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="영화 데이터 그래프 도감 1 - 시간", layout="wide")

# 앱 제목
st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown("일별 박스오피스 데이터를 바탕으로 시간에 따른 영화 흥행 추이를 분석합니다.")

# 데이터 불러오기 및 캐싱 (앱 속도 향상)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    df = pd.read_csv(url)
    
    # 8자리 숫자 형태의 날짜를 실제 datetime 형식으로 변환
    df['날짜'] = pd.to_datetime(df['날짜'].astype(str), format='%Y%m%d')
    return df

# 데이터 로드
try:
    df = load_data()
except Exception as e:
    st.error("데이터를 불러오는 데 실패했습니다. 인터넷 연결이나 URL을 확인해 주세요.")
    st.stop()


# ==========================================
# [구역 1] 영화별 일일 관객수 변화 (선 그래프)
# ==========================================
st.divider()
st.header("1. 영화별 일일 관객수 변화")

# 영화 선택 드롭다운
movie_list = df['영화명'].unique()
selected_movie = st.selectbox("그래프를 확인할 영화를 선택하세요:", movie_list)

# 선택한 영화 데이터 필터링
filtered_df = df[df['영화명'] == selected_movie]

# Plotly 선 그래프 생성
fig1 = px.line(
    filtered_df, 
    x="날짜", 
    y="일관객",
    markers=True,
    title=f"'{selected_movie}' 일 관객수 추이"
)

# 마우스 오버 툴팁(hover) 설정: 따옴표가 정상적으로 닫히도록 수정
fig1.update_traces(
    hovertemplate="<b>날짜:</b> %{x|%Y년 %m월 %d일}<br><b>일관객:</b> %{y:,.0f}명<extra></extra>"
)

# 그래프 레이아웃 다듬기
fig1.update_layout(
    xaxis_title="날짜",
    yaxis_title="일일 관객수 (명)",
    hovermode="x unified"
)

# 그래프 출력
st.plotly_chart(fig1, use_container_width=True)

# '이 그래프로 알 수 있는 것' 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** (이곳에 그래프가 보여주는 흥행 패턴, 피크 타임 등의 분석을 적어주세요)")


# ==========================================
# [구역 2] 총 관객수 TOP 5 영화의 일일 관객수 비교 (다중 선 그래프)
# ==========================================
st.divider()
st.header("2. 최고 흥행작 TOP 5 일일 관객수 비교")
st.markdown("전체 기간 동안 일관객 합계가 가장 높은 상위 5개 영화의 흥행 추이를 비교합니다. 우측 범례를 클릭하여 특정 영화를 켜거나 끌 수 있습니다.")

# 1. 영화별 전체 기간 '일관객' 합계 계산
movie_total_audience = df.groupby('영화명')['일관객'].sum().reset_index()

# 2. 합계 기준 상위 5개 영화 추출
top5_movies = movie_total_audience.sort_values(by='일관객', ascending=False).head(5)['영화명'].tolist()

# 3. 원본 데이터에서 상위 5개 영화 데이터만 필터링
top5_df = df[df['영화명'].isin(top5_movies)]

# 4. Plotly 다중 선 그래프 생성 (color='영화명'으로 구분)
fig2 = px.line(
    top5_df,
    x="날짜",
    y="일관객",
    color="영화명",
    markers=True,
    title="TOP 5 영화 일관객 추이 비교"
)

# 5. 그래프 레이아웃 및 툴팁 다듬기
fig2.update_traces(
    hovertemplate="<b>%{data.name}</b><br><b>날짜:</b> %{x|%Y년 %m월 %d일}<br><b>일관객:</b> %{y:,.0f}명"
)

fig2.update_layout(
    xaxis_title="날짜",
    yaxis_title="일일 관객수 (명)",
    hovermode="x unified",
    legend_title_text="영화명 (클릭)"
)

# 6. 그래프 출력
st.plotly_chart(fig2, use_container_width=True)

# '이 그래프로 알 수 있는 것' 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 총 관객수 상위 5개 영화들의 흥행 패턴 차이(예: 초반에 몰리는 영화 vs 꾸준히 관객을 유지하는 영화)를 한눈에 비교할 수 있습니다.")

# ==========================================
# [구역 3] 날짜별 극장가 총 관객수 변화 (영역 그래프)
# ==========================================
st.divider()
st.header("3. 날짜별 극장가 총 관객수 변화")
st.markdown("매일 10위권 영화들의 일일 관객수를 모두 합산하여, 극장가 전체의 방문객 추이를 영역 그래프로 살펴봅니다. 특히 관객이 가장 많았던 3일을 강조하여 보여줍니다.")

# 1. 날짜별 '일관객' 합계 계산
daily_total = df.groupby('날짜')['일관객'].sum().reset_index()

# 2. Plotly 영역 그래프 생성
fig3 = px.area(
    daily_total,
    x="날짜",
    y="일관객",
    title="날짜별 10위권 일일 관객수 합계"
)

# 3. 툴팁 및 레이아웃 다듬기
fig3.update_traces(
    hovertemplate="<b>날짜:</b> %{x|%Y년 %m월 %d일}<br><b>총 일관객:</b> %{y:,.0f}명"
)
fig3.update_layout(
    xaxis_title="날짜",
    yaxis_title="총 일일 관객수 (명)",
    hovermode="x unified"
)

# 4. 관객수 합계가 가장 컸던 날 Top 3 추출
top3_days = daily_total.nlargest(3, '일관객')

# 5. Top 3 날짜에 주석(Annotation) 추가하기
for index, row in top3_days.iterrows():
    # 날짜를 읽기 쉬운 문자열 형태로 변환
    date_str = row['날짜'].strftime('%Y-%m-%d')
    audience_cnt = row['일관객']
    
    # 그래프에 화살표와 텍스트 추가
    fig3.add_annotation(
        x=row['날짜'],
        y=row['일관객'],
        text=f"🏆 {date_str}<br>({audience_cnt:,.0f}명)",
        showarrow=True,
        arrowhead=2,          # 화살표 머리 모양
        arrowsize=1,          # 화살표 크기
        arrowwidth=2,         # 화살표 두께
        arrowcolor="#E36414", # 화살표 색상
        ax=0,                 # 텍스트의 x축 위치 조정 (0은 화살표와 수직)
        ay=-45,               # 텍스트의 y축 위치 조정 (-45는 위로 띄움)
        font=dict(color="#E36414", size=12, family="Arial"),
        bgcolor="white",
        bordercolor="#E36414",
        borderwidth=1,
        borderpad=4
    )

# 6. 그래프 출력
st.plotly_chart(fig3, use_container_width=True)

# '이 그래프로 알 수 있는 것' 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 명절, 공휴일, 혹은 특정 대작이 개봉한 주말 등 1년 중 사람들이 극장에 가장 많이 몰리는 시기를 파악할 수 있습니다.")

# ==========================================
# [구역 4] 최고 흥행작 TOP 10 누적 관객수 및 진입 일수 (가로 막대그래프)
# ==========================================
st.divider()
st.header("4. 최고 흥행작 TOP 10 누적 관객수")
st.markdown("전체 기간 동안 가장 많은 관객을 동원한 영화 10편을 순위대로 보여줍니다. 막대에 마우스를 올리면 10위권에 머문 날짜 수도 확인할 수 있습니다.")

# 1. 영화별 총 관객수와 10위권 진입 일수 계산
# 각 행이 하루 치 10위권 기록이므로, 행의 개수(count)가 곧 10위권 진입 일수가 됩니다.
movie_stats = df.groupby('영화명').agg(
    총관객수=('일관객', 'sum'),
    진입일수=('날짜', 'count')
).reset_index()

# 2. 총관객수 기준 상위 10개 영화 추출
top10_movies = movie_stats.nlargest(10, '총관객수')

# 3. 플롯리 가로 막대그래프는 데이터의 아래쪽 행부터 위로 그려집니다.
# 관객수가 가장 많은 영화가 맨 위에 오도록 데이터를 오름차순 정렬합니다.
top10_movies = top10_movies.sort_values(by='총관객수', ascending=True)

# 4. Plotly 가로 막대그래프 생성
fig4 = px.bar(
    top10_movies,
    x="총관객수",
    y="영화명",
    orientation='h',
    title="TOP 10 영화 누적 관객수 및 진입 일수",
    custom_data=['진입일수'] # 툴팁에 사용할 추가 데이터 전달
)

# 5. 툴팁 및 레이아웃 다듬기
# customdata[0]을 통해 전달받은 '진입일수'를 표시합니다.
fig4.update_traces(
    hovertemplate="<b>%{y}</b><br><b>총 관객수:</b> %{x:,.0f}명<br><b>10위권 진입 일수:</b> %{customdata[0]}일<extra></extra>",
    marker_color="#457b9d" # 막대 색상 지정하여 시각적 안정감 부여
)

fig4.update_layout(
    xaxis_title="총 관객수 (명)",
    yaxis_title="영화명"
)

# 6. 그래프 출력
st.plotly_chart(fig4, use_container_width=True)

# '이 그래프로 알 수 있는 것' 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 단기간에 폭발적인 인기를 끌어 상위권을 차지한 영화와, 순위는 압도적이지 않아도 오랫동안 10위권에 머물러 누적 관객이 많은 영화를 비교해 볼 수 있습니다.")
