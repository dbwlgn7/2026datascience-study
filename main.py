import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="영화 데이터 그래프 도감 2", layout="wide")

@st.cache_data
def load_data():
    """
    지정된 URL에서 영화 데이터를 불러오고 요구사항에 맞게 전처리합니다.
    """
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)
    
    # 장르(genre) 전처리: 세로막대(|)로 구분된 경우 첫 번째 장르만 추출
    df['genre'] = df['genre'].apply(lambda x: x.split('|')[0] if isinstance(x, str) else x)
    
    return df

st.title("영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown("1년간 박스오피스 10위권에 든 영화 중 해당 기간에 개봉한 216편의 데이터입니다.")

# 데이터 로딩
df = load_data()

st.subheader("1. 장르별 영화 개봉 편수 (분포)")

# 장르별 영화 편수 계산
genre_counts = df['genre'].value_counts().reset_index()
genre_counts.columns = ['장르', '편수']

# 플롯리 도넛 그래프 생성 (hole 파라미터로 도넛 모양 구현)
fig_donut = px.pie(
    genre_counts, 
    values='편수', 
    names='장르', 
    hole=0.4,
    title='장르별 개봉 비중'
)

# 조각에 마우스를 올렸을 때 편수와 비율이 보이도록 호버 템플릿 설정
fig_donut.update_traces(
    textposition='inside', 
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>편수: %{value}편<br>비율: %{percent}<extra></extra>"
)

# 그래프 화면에 출력
st.plotly_chart(fig_donut, use_container_width=True)

# '이 그래프로 알 수 있는 것' 한 문장 자리 마련
st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 도넛 그래프를 통해 파악한 가장 비중이 큰 장르 등 핵심 정보 한 문장을 적어주세요.")

# 구역 나누기 (선 긋기)
st.divider()

# 이후 추가될 다른 그래프들을 위한 자리 (필요 시 아래에 이어서 작성)
# st.subheader("2. 다음 그래프 제목")
# ...
