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
    
    # --- 추가된 부분: 트리맵 에러 방지용 결측치(NaN) 처리 ---
    # Plotly 트리맵은 path에 빈칸(NaN)이 있으면 에러가 발생하므로 문자로 채워줍니다.
    df['genre'] = df['genre'].fillna('기타장르').astype(str)
    df['movieNm'] = df['movieNm'].fillna('알수없음').astype(str)
    df['total_audi'] = pd.to_numeric(df['total_audi'], errors='coerce').fillna(0)
    
    # 관객 수가 0보다 큰 정상적인 데이터만 남기기
    df = df[df['total_audi'] > 0]
    
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

st.subheader("2. 장르별 총 관객 수 (트리맵)")

# 플롯리 트리맵 생성: 장르 안에 영화가 포함되도록 계층 구조 설정 (크기는 총 관객 수)
fig_treemap = px.treemap(
    df,
    path=['genre', 'movieNm'],
    values='total_audi',
    title='장르 및 영화별 총 관객 수'
)

# 칸에 마우스를 올렸을 때 이름(영화명 또는 장르명)과 총 관객 수가 보이도록 호버 템플릿 설정
fig_treemap.update_traces(
    hovertemplate="<b>%{label}</b><br>총 관객 수: %{value:,}명<extra></extra>"
)

# 그래프 화면에 출력
st.plotly_chart(fig_treemap, use_container_width=True)

# '이 그래프로 알 수 있는 것' 한 문장 자리 마련
st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 트리맵을 통해 파악한 가장 많은 관객을 동원한 장르나 특정 영화 등 핵심 정보 한 문장을 적어주세요.")

# 구역 나누기 (선 긋기)
st.divider()

st.subheader("3. 총 관객 수 분포 (히스토그램)")

# 플롯리 히스토그램 생성: 총 관객 수의 분포 시각화
fig_hist = px.histogram(
    df,
    x='total_audi',
    nbins=10, # 막대의 개수 설정
    title='총 관객 수 분포 (어느 구간에 영화가 가장 많을까?)',
    labels={'total_audi': '총 관객 수'}
)

# 칸(막대)에 마우스를 올렸을 때 상세 정보가 보이도록 설정
fig_hist.update_traces(
    hovertemplate="<b>관객 수 구간:</b> %{x}<br><b>영화 편수:</b> %{y}편<extra></extra>"
)
fig_hist.update_layout(
    yaxis_title="영화 편수",
    xaxis_title="총 관객 수 (명)"
)

# 그래프 화면에 출력
st.plotly_chart(fig_hist, use_container_width=True)

# 1. 가장 관객이 많은 영화 찾기
max_audi_movie = df.loc[df['total_audi'].idxmax()]
best_movie_name = max_audi_movie['movieNm']
best_movie_audi = max_audi_movie['total_audi']

# 2. 가장 영화가 많이 몰려 있는 구간 찾기 (pandas의 cut 기능 활용)
bins = pd.cut(df['total_audi'], bins=10)
most_freq_bin = bins.value_counts().idxmax()

# 구간의 시작과 끝 계산 (통계 계산상 첫 구간의 시작이 음수로 나오는 것을 방지하기 위해 max 0 처리)
start_audi = max(0, int(most_freq_bin.left))
end_audi = int(most_freq_bin.right)

# '이 그래프로 알 수 있는 것' 문구 출력 (위에서 계산된 데이터를 동적으로 삽입)
st.info(f"**💡 이 그래프로 알 수 있는 것:**\n\n"
        f"✔️ 이 기간 개봉한 영화들의 총 관객 수는 오른쪽으로 긴 꼬리를 가진 분포를 보입니다. 즉, 대부분의 영화가 **{start_audi:,}명 ~ {end_audi:,}명** 구간에 몰려 있습니다.\n\n"
        f"✔️ 가장 압도적으로 많은 관객을 동원한 영화는 **'{best_movie_name}'**(총 관객 약 {best_movie_audi:,}명)입니다.")

# 구역 나누기 (선 긋기)
st.divider()

st.subheader("4. 개봉일 스크린 수와 총 관객 수의 관계 (산점도)")

# 플롯리 산점도 생성: 스크린 수와 총 관객 수의 상관관계 시각화
fig_scatter = px.scatter(
    df,
    x='first_scrn',
    y='total_audi',
    color='genre',        # 장르별로 점 색상 다르게 표시
    hover_name='movieNm', # 마우스를 올렸을 때 영화명이 가장 위에 표시되도록 설정
    title='개봉일 스크린 수 vs 총 관객 수',
    labels={
        'first_scrn': '개봉일 스크린 수 (개)',
        'total_audi': '총 관객 수 (명)',
        'genre': '장르'
    }
)

# 겹쳐있는 점들이 잘 보이도록 약간의 투명도(opacity)를 주고 툴팁 내용 수정
fig_scatter.update_traces(
    marker=dict(size=9, opacity=0.7),
    hovertemplate="<b>%{hovertext}</b><br><br>" +
                  "개봉일 스크린 수: %{x}개<br>" +
                  "총 관객 수: %{y:,}명<extra></extra>"
)

# 그래프 화면에 출력
st.plotly_chart(fig_scatter, use_container_width=True)

# '이 그래프로 알 수 있는 것' 한 문장 자리 마련
st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 개봉일 스크린 수가 많을수록 총 관객 수도 늘어나는 경향(양의 상관관계)이 있는지, 혹은 특정 장르가 두드러지는 특징이 있는지 등 핵심 정보 한 문장을 적어주세요.")

# 구역 나누기 (선 긋기)
st.divider()
