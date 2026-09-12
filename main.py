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
    
    # 트리맵, 선버스트 등 계층 그래프 에러 방지용 결측치(NaN) 처리
    df['genre'] = df['genre'].fillna('기타장르').astype(str)
    df['movieNm'] = df['movieNm'].fillna('알수없음').astype(str)
    df['nation'] = df['nation'].fillna('알수없음').astype(str)
    
    # 숫자형 데이터 변환 (빈칸이나 잘못된 문자는 0으로 처리)
    df['total_audi'] = pd.to_numeric(df['total_audi'], errors='coerce').fillna(0)
    df['first_week_audi'] = pd.to_numeric(df['first_week_audi'], errors='coerce').fillna(0)
    
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

# 플롯리 도넛 그래프 생성
fig_donut = px.pie(
    genre_counts, 
    values='편수', 
    names='장르', 
    hole=0.4,
    title='장르별 개봉 비중'
)

fig_donut.update_traces(
    textposition='inside', 
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>편수: %{value}편<br>비율: %{percent}<extra></extra>"
)

st.plotly_chart(fig_donut, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 도넛 그래프를 통해 파악한 가장 비중이 큰 장르 등 핵심 정보 한 문장을 적어주세요.")

st.divider()

st.subheader("2. 장르별 총 관객 수 (트리맵)")

# 플롯리 트리맵 생성
fig_treemap = px.treemap(
    df,
    path=['genre', 'movieNm'],
    values='total_audi',
    title='장르 및 영화별 총 관객 수'
)

fig_treemap.update_traces(
    hovertemplate="<b>%{label}</b><br>총 관객 수: %{value:,}명<extra></extra>"
)

st.plotly_chart(fig_treemap, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 트리맵을 통해 파악한 가장 많은 관객을 동원한 장르나 특정 영화 등 핵심 정보 한 문장을 적어주세요.")

st.divider()

st.subheader("3. 총 관객 수 분포 (히스토그램)")

# 플롯리 히스토그램 생성
fig_hist = px.histogram(
    df,
    x='total_audi',
    nbins=10,
    title='총 관객 수 분포 (어느 구간에 영화가 가장 많을까?)',
    labels={'total_audi': '총 관객 수'}
)

fig_hist.update_traces(
    hovertemplate="<b>관객 수 구간:</b> %{x}<br><b>영화 편수:</b> %{y}편<extra></extra>"
)
fig_hist.update_layout(
    yaxis_title="영화 편수",
    xaxis_title="총 관객 수 (명)"
)

st.plotly_chart(fig_hist, use_container_width=True)

# 가장 관객이 많은 영화 및 밀집 구간 찾기
max_audi_movie = df.loc[df['total_audi'].idxmax()]
best_movie_name = max_audi_movie['movieNm']
best_movie_audi = max_audi_movie['total_audi']

bins = pd.cut(df['total_audi'], bins=10)
most_freq_bin = bins.value_counts().idxmax()
start_audi = max(0, int(most_freq_bin.left))
end_audi = int(most_freq_bin.right)

st.info(f"**💡 이 그래프로 알 수 있는 것:**\n\n"
        f"✔️ 이 기간 개봉한 영화들의 총 관객 수는 오른쪽으로 긴 꼬리를 가진 분포를 보입니다. 즉, 대부분의 영화가 **{start_audi:,}명 ~ {end_audi:,}명** 구간에 몰려 있습니다.\n\n"
        f"✔️ 가장 압도적으로 많은 관객을 동원한 영화는 **'{best_movie_name}'**(총 관객 약 {best_movie_audi:,}명)입니다.")

st.divider()

st.subheader("4. 개봉일 스크린 수와 총 관객 수의 관계 (산점도)")

# 플롯리 산점도 생성
fig_scatter = px.scatter(
    df,
    x='first_scrn',
    y='total_audi',
    color='genre',
    hover_name='movieNm',
    title='개봉일 스크린 수 vs 총 관객 수',
    labels={
        'first_scrn': '개봉일 스크린 수 (개)',
        'total_audi': '총 관객 수 (명)',
        'genre': '장르'
    }
)

fig_scatter.update_traces(
    marker=dict(size=9, opacity=0.7),
    hovertemplate="<b>%{hovertext}</b><br><br>" +
                  "개봉일 스크린 수: %{x}개<br>" +
                  "총 관객 수: %{y:,}명<extra></extra>"
)

st.plotly_chart(fig_scatter, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 개봉일 스크린 수가 많을수록 총 관객 수도 늘어나는 경향(양의 상관관계)이 있는지, 혹은 특정 장르가 두드러지는 특징이 있는지 등 핵심 정보 한 문장을 적어주세요.")

st.divider()

st.subheader("5. 장르별 총 관객 수 분포 (상자 그림)")

# 10편 이상인 장르만 골라내기
genre_counts_for_box = df['genre'].value_counts()
valid_genres = genre_counts_for_box[genre_counts_for_box >= 10].index
filtered_df = df[df['genre'].isin(valid_genres)]

# 플롯리 상자 그림(박스플롯) 생성
fig_box = px.box(
    filtered_df,
    x='genre',
    y='total_audi',
    color='genre',
    hover_name='movieNm',
    title='장르별 총 관객 수 분포 (영화 10편 이상 장르만)',
    labels={
        'genre': '장르',
        'total_audi': '총 관객 수 (명)'
    }
)

fig_box.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>총 관객 수: %{y:,}명<extra></extra>"
)

st.plotly_chart(fig_box, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 상자 그림을 통해 파악한 특정 장르의 관객 수 편차나, 이례적으로 흥행한(상자 위로 튀어나온) 영화에 대한 핵심 정보 한 문장을 적어주세요.")

st.divider()

st.subheader("6. 스크린 수, 총 관객 수, 첫 주 관객 수의 관계 (버블 차트)")

# 플롯리 버블 차트 생성 (산점도 + size 파라미터)
fig_bubble = px.scatter(
    df,
    x='first_scrn',
    y='total_audi',
    color='genre',
    size='first_week_audi',          # 원의 크기를 첫 주 관객 수로 지정
    hover_name='movieNm',
    custom_data=['first_week_audi'], # 툴팁에 원래 숫자를 표시하기 위해 데이터 전달
    size_max=50,                     # 가장 큰 원의 최대 크기 제한
    title='개봉일 스크린 수 vs 총 관객 수 (원의 크기: 첫 주 관객 수)',
    labels={
        'first_scrn': '개봉일 스크린 수 (개)',
        'total_audi': '총 관객 수 (명)',
        'genre': '장르',
        'first_week_audi': '첫 주 관객 수 (명)'
    }
)

# 겹치는 점이 잘 보이도록 투명도, 테두리를 주고 툴팁 내용 구성
fig_bubble.update_traces(
    marker=dict(opacity=0.6, line=dict(width=0.5, color='gray')),
    hovertemplate="<b>%{hovertext}</b><br><br>" +
                  "개봉일 스크린 수: %{x}개<br>" +
                  "총 관객 수: %{y:,}명<br>" +
                  "첫 주 관객 수: %{customdata[0]:,}명<extra></extra>"
)

st.plotly_chart(fig_bubble, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 원의 크기(첫 주 관객 수)가 클수록 최종 관객 수도 높은지(비례하는지), 혹은 첫 주만 반짝하고 멈춘 예외적인 영화가 있는지 등 핵심 정보 한 문장을 적어주세요.")

st.divider()

st.subheader("7. 제작 국가 및 장르별 영화 편수 (선버스트)")

# 선버스트 차트에 영화 편수를 나타내기 위해 각 행을 1편으로 계산할 기준(movie_count) 추가
df_sunburst = df.copy()
df_sunburst['movie_count'] = 1

# 플롯리 선버스트 차트 생성
fig_sunburst = px.sunburst(
    df_sunburst,
    path=['nation', 'genre'],
    values='movie_count',
    title='제작 국가에서 장르로 이어지는 영화 편수'
)

fig_sunburst.update_traces(
    hovertemplate="<b>%{label}</b><br>영화 편수: %{value}편<extra></extra>"
)

st.plotly_chart(fig_sunburst, use_container_width=True)

st.info("**💡 이 그래프로 알 수 있는 것:** 이곳에 선버스트 차트를 통해 파악한 어느 국가의 영화가 가장 많이 개봉했는지, 혹은 특정 국가의 주력 장르가 무엇인지 등 핵심 정보 한 문장을 적어주세요.")

st.divider()
