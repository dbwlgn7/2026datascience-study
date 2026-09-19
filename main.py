import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

st.set_page_config(page_title="영화 흥행 예측기", layout="wide")


# 1. 데이터 불러오기
@st.cache_data
def load_data():
    daily_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    movies_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"

    df_daily = pd.read_csv(daily_url, encoding="utf-8")
    df_movies = pd.read_csv(movies_url, encoding="utf-8")

    return df_daily, df_movies


df_daily, df_movies = load_data()

# 기준 기간 추출
dates = df_daily["날짜"].astype(str)
min_date = f"{dates.min()[:4]}-{dates.min()[4:6]}-{dates.min()[6:]}"
max_date = f"{dates.max()[:4]}-{dates.max()[4:6]}-{dates.max()[6:]}"

st.title("🎬 영화 흥행 예측기 (다중 회귀 분석)")
st.info(f"📅 **박스오피스 기준 기간:** {min_date} ~ {max_date}")

# 2. 상위 10개 행 출력
st.subheader("📋 영화별 데이터 (상위 10행)")
st.dataframe(df_movies.head(10), use_container_width=True)

# 3. 데이터 정렬 및 분할 (영화코드 순 정렬 후 10편 중 앞 3편 테스트)
df_movies = df_movies.sort_values("movieCd").reset_index(drop=True)
test_mask = (df_movies.index % 10) < 3

train_count = (~test_mask).sum()
test_count = test_mask.sum()

# 4. 예측 변수 선택 (체크박스)
st.subheader("⚙️ 모델 학습 변수 선택")

candidate_features = {
    "first_scrn": "첫 관측일 스크린수",
    "first_show": "첫 관측일 상영횟수",
    "peak": "성수기 개봉 여부 (1/0)",
    "first_week_audi": "첫 주 관객수",
    "days_in_top10": "10위권 유지 일수",
    "genre": "장르",
    "nation": "국가",
}

selected_features = []
cols = st.columns(len(candidate_features))

for idx, (col, label) in enumerate(candidate_features.items()):
    with cols[idx]:
        # 기본 선택값 설정
        default_val = col in [
            "first_scrn",
            "first_week_audi",
            "days_in_top10",
            "peak",
        ]
        if st.checkbox(f"{label}\n(`{col}`)", value=default_val):
            selected_features.append(col)

if not selected_features:
    st.warning("⚠️ 최소 하나 이상의 변수를 선택해 주세요.")
    st.stop()

# 5. 전처리 및 모델 학습
X_raw = df_movies[selected_features].fillna(0)
# 범주형 변수가 선택된 경우 원-핫 인코딩 처리
X = pd.get_dummies(X_raw, drop_first=True)
y = df_movies["total_audi"]

X_train, X_test = X[~test_mask], X[test_mask]
y_train, y_test = y[~test_mask], y[test_mask]

model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

# 평가 지표 계산
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)

# 6. 학습 정보 및 평가 결과 출력
st.markdown("---")
st.subheader("📊 모델 평가 및 학습 정보")

col1, col2, col3, col4 = st.columns(4)
col1.metric("학습 영화 수", f"{train_count} 편")
col2.metric("평가(테스트) 영화 수", f"{test_count} 편")
col3.metric("결정계수 (R² Score)", f"{r2:.4f}")
col4.metric("평균 절대 오차 (MAE)", f"{mae:,.0f} 명")

# 7. 시각화 (Plotly 산점도)
st.subheader("📈 실제 vs 예측 관객 수 (로그 축)")

# 1,000명 미만 예측 영화 처리
under_1000_mask = y_pred < 1000
under_1000_count = np.sum(under_1000_mask)

# 그래프 시각화용 예측값 (1,000 미만은 1,000으로 보정하여 바닥에 표시)
y_pred_plot = np.where(y_pred < 1000, 1000, y_pred)

plot_df = pd.DataFrame(
    {
        "영화명": df_movies.loc[test_mask, "movieNm"],
        "실제 관객수": y_test,
        "예측 관객수(원래)": y_pred,
        "예측 관객수(표시용)": y_pred_plot,
    }
)

fig = go.Figure()

# 산점도 추가
fig.add_trace(
    go.Scatter(
        x=plot_df["실제 관객수"],
        y=plot_df["예측 관객수(표시용)"],
        mode="markers",
        text=plot_df["영화명"],
        hovertemplate="<b>%{text}</b><br>실제 관객: %{x:,.0f}명<br>예측 관객: %{customdata:,.0f}명<extra></extra>",
        customdata=plot_df["예측 관객수(원래)"],
        name="테스트 영화",
        marker=dict(size=8, color="#1f77b4", opacity=0.7),
    )
)

# 실제 = 예측 대각선 추가
min_val = min(y_test.min(), 1000)
max_val = max(y_test.max(), y_pred_plot.max())

fig.add_trace(
    go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode="lines",
        name="기준선 (실제 = 예측)",
        line=dict(color="red", dash="dash"),
    )
)

# 축 설정 (로그 축)
fig.update_xaxes(type="log", title="실제 총 관객 수 (로그 축)")
fig.update_yaxes(type="log", title="예측 총 관객 수 (로그 축)")

fig.update_layout(
    height=600,
    hovermode="closest",
    legend=dict(x=0.01, y=0.99),
)

st.plotly_chart(fig, use_container_width=True)

if under_1000_count > 0:
    st.info(
        f"💡 예측 관객 수가 **1,000명 미만**으로 산출된 영화는 총 **{under_1000_count}편**이며, 그래프 바닥(Y축 1,000 위치)에 표시되었습니다."
    )
else:
    st.info("💡 예측 관객 수가 1,000명 미만인 영화가 없습니다.")
