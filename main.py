import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# 1. 페이지 설정 및 브라우저 탭 제목 설정
st.set_page_config(
    page_title="영화 유형 나누기",
    page_icon="🎬",
    layout="wide"
)

# 2. 메인 타이틀
st.title("🎬 영화 유형 나누기")

# 3. 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_preprocess_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    raw_df = pd.read_csv(url, encoding="utf-8")
    
    total_raw_count = len(raw_df)
    
    # 필수 열 유효성 검사 및 결측치/0 값 제거
    req_cols = ['first_scrn', 'total_audi', 'days_in_top10', 'first_week_audi', 'movieNm']
    clean_df = raw_df.dropna(subset=req_cols).copy()
    
    # 첫 주 관객이 0이거나 스크린 수/누적 관객이 0 이하인 데이터 제거 (로그 계산 및 롱런지수 계산 유효성)
    clean_df = clean_df[
        (clean_df['first_week_audi'] > 0) & 
        (clean_df['first_scrn'] > 0) & 
        (clean_df['total_audi'] > 0)
    ].copy()
    
    # 파생 속성 생성
    clean_df['log_first_scrn'] = np.log10(clean_df['first_scrn'])
    clean_df['log_total_audi'] = np.log10(clean_df['total_audi'])
    clean_df['long_run_index'] = (clean_df['total_audi'] / clean_df['first_week_audi']).clip(upper=20)
    
    return raw_df, clean_df, total_raw_count

# 데이터 로드
raw_df, df, total_raw_count = load_and_preprocess_data()
filtered_count = len(df)

# 4. 전체 편수 및 분석 대상 편수 표시 (한 줄)
st.markdown(f"**전체 영화 수:** {total_raw_count:,}편 &nbsp;|&nbsp; **분석 대상 영화 수:** {filtered_count:,}편")
st.divider()

# 속성 매핑 (화면 표시 이름 -> 내부 컬럼 이름)
feature_map = {
    "스크린 수 (상용로그)": "log_first_scrn",
    "누적 관객 (상용로그)": "log_total_audi",
    "10위권 일수": "days_in_top10",
    "롱런 지수": "long_run_index"
}

# 5. 군집화에 사용할 속성 선택 UI (기본 4개 모두 선택)
st.subheader("1. 군집화 속성 선택")
selected_labels = st.multiselect(
    "군집화(K-Means)에 사용할 속성을 선택하세요 (최소 2개 이상):",
    options=list(feature_map.keys()),
    default=list(feature_map.keys())
)

# 속성이 2개 미만일 경우 처리
if len(selected_labels) < 2:
    st.warning("⚠️ 군집화를 수행하려면 속성을 2개 이상 선택해야 합니다.")
    st.stop()

# 6. 데이터 표준화 및 K-평균 군집화 (k=3, random_state 고정)
selected_cols = [feature_map[label] for label in selected_labels]

scaler = StandardScaler()
scaled_features = scaler.fit_transform(df[selected_cols])

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df['raw_cluster'] = kmeans.fit_predict(scaled_features)

# 누적 관객 평균(원래 단위)이 큰 순서대로 ㉮, ㉯, ㉰ 부여
cluster_audi_mean = df.groupby('raw_cluster')['total_audi'].mean()
sorted_raw_clusters = cluster_audi_mean.sort_values(ascending=False).index.tolist()

label_mapping = {
    sorted_raw_clusters[0]: '㉮',
    sorted_raw_clusters[1]: '㉯',
    sorted_raw_clusters[2]: '㉰'
}

df['cluster'] = df['raw_cluster'].map(label_mapping)
df['cluster'] = pd.Categorical(df['cluster'], categories=['㉮', '㉯', '㉰'], ordered=True)

# 시각화 색상 설정
cluster_colors = {'㉮': '#EF553B', '㉯': '#636EFA', '㉰': '#00CC96'}

# 7. 2차원 산점도
st.divider()
st.subheader("2. 2차원 산점도")

col1, col2 = st.columns(2)
with col1:
    x_label = st.selectbox("2D X축 속성 선택", options=list(feature_map.keys()), index=0)
with col2:
    y_label = st.selectbox("2D Y축 속성 선택", options=list(feature_map.keys()), index=1)

x_col = feature_map[x_label]
y_col = feature_map[y_label]

fig_2d = px.scatter(
    df,
    x=x_col,
    y=y_col,
    color='cluster',
    hover_name='movieNm',
    hover_data={
        'cluster': True,
        'first_scrn': ':,',
        'total_audi': ':,',
        'days_in_top10': ':.1f',
        'long_run_index': ':.2f'
    },
    labels={
        x_col: x_label,
        y_col: y_label,
        'cluster': '유형 (묶음)'
    },
    color_discrete_map=cluster_colors,
    category_orders={'cluster': ['㉮', '㉯', '㉰']},
    title=f"2차원 산점도 ({x_label} vs {y_label})"
)
fig_2d.update_traces(marker=dict(size=6, opacity=0.8))
st.plotly_chart(fig_2d, use_container_width=True)

# 8. 3차원 산점도
st.divider()
st.subheader("3. 3차원 산점도")

if len(selected_labels) < 3:
    st.info("💡 3차원 산점도를 그리려면 위에서 군집화 속성을 3개 이상 선택해 주세요.")
else:
    col_x, col_y, col_z = st.columns(3)
    with col_x:
        x_3d_label = st.selectbox("3D X축 속성 선택", options=selected_labels, index=0)
    with col_y:
        y_3d_label = st.selectbox("3D Y축 속성 선택", options=selected_labels, index=1 if len(selected_labels) > 1 else 0)
    with col_z:
        z_3d_label = st.selectbox("3D Z축 속성 선택", options=selected_labels, index=2 if len(selected_labels) > 2 else 0)

    fig_3d = px.scatter_3d(
        df,
        x=feature_map[x_3d_label],
        y=feature_map[y_3d_label],
        z=feature_map[z_3d_label],
        color='cluster',
        hover_name='movieNm',
        hover_data={
            'cluster': True,
            'first_scrn': ':,',
            'total_audi': ':,',
            'days_in_top10': ':.1f',
            'long_run_index': ':.2f'
        },
        labels={
            feature_map[x_3d_label]: x_3d_label,
            feature_map[y_3d_label]: y_3d_label,
            feature_map[z_3d_label]: z_3d_label,
            'cluster': '유형 (묶음)'
        },
        color_discrete_map=cluster_colors,
        category_orders={'cluster': ['㉮', '㉯', '㉰']},
        title="3차원 산점도 (마우스로 드래그하여 회전할 수 있습니다)"
    )
    fig_3d.update_traces(marker=dict(size=3, opacity=0.8))
    st.plotly_chart(fig_3d, use_container_width=True)

# 9. 묶음별 영화 편수 및 속성 평균 표 (원래 단위)
st.divider()
st.subheader("4. 묶음(유형)별 통계 요약")

summary_df = df.groupby('cluster', observed=False).agg(
    영화_편수=('movieNm', 'count'),
    평균_스크린_수=('first_scrn', 'mean'),
    평균_누적_관객=('total_audi', 'mean'),
    평균_10위권_일수=('days_in_top10', 'mean'),
    평균_롱런_지수=('long_run_index', 'mean')
).reset_index()

summary_df.columns = [
    "유형", "영화 편수", "스크린 수 평균", "누적 관객 평균", "10위권 일수 평균", "롱런 지수 평균"
]

# 서식 적용
formatted_summary = summary_df.copy()
formatted_summary["영화 편수"] = formatted_summary["영화 편수"].map("{:,}편".format)
formatted_summary["스크린 수 평균"] = formatted_summary["스크린 수 평균"].map("{:,.1f}개".format)
formatted_summary["누적 관객 평균"] = formatted_summary["누적 관객 평균"].map("{:,.0f}명".format)
formatted_summary["10위권 일수 평균"] = formatted_summary["10위권 일수 평균"].map("{:.1f}일".format)
formatted_summary["롱런 지수 평균"] = formatted_summary["롱런 지수 평균"].map("{:.2f}".format)

st.dataframe(formatted_summary, use_container_width=True)

# 10. 묶음별 누적 관객 탑 5 영화
st.divider()
st.subheader("5. 묶음(유형)별 누적 관객 TOP 5 영화")

top5_cols = st.columns(3)
clusters = ['㉮', '㉯', '㉰']

for idx, cluster in enumerate(clusters):
    with top5_cols[idx]:
        st.markdown(f"### 유형 **{cluster}**")
        cluster_movies = df[df['cluster'] == cluster].sort_values(by='total_audi', ascending=False).head(5)
        
        for rank, (_, row) in enumerate(cluster_movies.iterrows(), 1):
            st.markdown(f"**{rank}. {row['movieNm']}**")
            st.caption(f"관객 수: {row['total_audi']:,}명 | 스크린: {row['first_scrn']:,}개")
