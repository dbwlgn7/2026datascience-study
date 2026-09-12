import streamlit as st
import pandas as pd
import plotly.express as px

페이지 기본 설정

st.set_page_config(page_title="영화 데이터 그래프 도감 1 - 시간", layout="wide")

앱 제목

st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown("일별 박스오피스 데이터를 바탕으로 시간에 따른 영화 흥행 추이를 분석합니다.")

데이터 불러오기 및 캐싱 (앱 속도 향상)

@st.cache_data
def load_data():
url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
df = pd.read_csv(url)

# 8자리 숫자 형태의 날짜를 실제 datetime 형식으로 변환
df['날짜'] = pd.to_datetime(df['날짜'].astype(str), format='%Y%m%d')
return df


데이터 로드

try:
df = load_data()
except Exception as e:
st.error("데이터를 불러오는 데 실패했습니다. 인터넷 연결이나 URL을 확인해 주세요.")
st.stop()

==========================================

[구역 1] 영화별 일일 관객수 변화 (선 그래프)

==========================================

st.divider()
st.header("1. 영화별 일일 관객수 변화")

영화 선택 드롭다운

movie_list = df['영화명'].unique()
selected_movie = st.selectbox("그래프를 확인할 영화를 선택하세요:", movie_list)

선택한 영화 데이터 필터링

filtered_df = df[df['영화명'] == selected_movie]

Plotly 선 그래프 생성

fig1 = px.line(
filtered_df,
x="날짜",
y="일관객",
markers=True,
title=f"'{selected_movie}' 일 관객수 추이"
)

마우스 오버 툴팁(hover) 설정: 날짜와 관객수가 직관적으로 보이게 포맷팅

fig1.update_traces(
hovertemplate="날짜: %{x|%Y년 %m월 %d일}



일관객: %{y:,.0f}명"
)

그래프 레이아웃 다듬기

fig1.update_layout(
xaxis_title="날짜",
yaxis_title="일일 관객수 (명)",
hovermode="x unified"
)

그래프 출력

st.plotly_chart(fig1, use_container_width=True)

'이 그래프로 알 수 있는 것' 문구 자리

st.info("💡 이 그래프로 알 수 있는 것: (이곳에 그래프가 보여주는 흥행 패턴, 피크 타임 등의 분석을 적어주세요)")

==========================================

[구역 2] 새로운 그래프 추가를 위한 빈 구역

==========================================

st.divider()
st.header("2. (새로운 그래프 제목을 입력하세요)")
st.write("앞으로 추가될 두 번째 그래프가 들어갈 자리입니다.")

차후 여기에 새로운 데이터 필터링과 st.plotly_chart() 등을 추가하시면 됩니다.

st.info("💡 이 그래프로 알 수 있는 것: (...)")
