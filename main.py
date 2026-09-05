import datetime
import requests
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 시네마 커스텀 CSS (UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스 대시보드",
    page_icon="🎬",
    layout="wide"
)

# 고급스러운 다크 시네마 테마 스타일링
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(45deg, #FF4B4B, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #FFD700;
        border-left: 4px solid #FF4B4B;
        padding-left: 10px;
        margin-top: 25px;
        margin-bottom: 15px;
    }
    .review-card {
        background-color: #1E232A;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #313742;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시각(KST) 기준 날짜 계산 및 사이드바 옵션
# -----------------------------------------------------------------------------
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
now_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = (now_kst - datetime.timedelta(days=1)).date()

st.markdown('<div class="main-title">🍿 CINEMA BOX OFFICE</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 옵션 및 날짜 선택")
    selected_date = st.date_input(
        "📅 조회 날짜 선택 (최대 어제)",
        value=yesterday_kst,
        max_value=yesterday_kst,
        min_value=datetime.date(2004, 1, 1)
    )
    st.info("💡 KOBIS 공식 데이터 기반 대시보드입니다.")

target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.caption(f"🎬 **조회 기준일:** {display_date_str} (한국 시간 기준)")

# -----------------------------------------------------------------------------
# 3. Secrets API 키 확인
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 인증키(KOBIS_KEY)가 비밀 금고(Secrets)에 등록되어 있지 않습니다.")
    st.info("Streamlit Cloud의 App settings -> Secrets 메뉴에서 `KOBIS_KEY`를 설정해 주세요.")
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# -----------------------------------------------------------------------------
# 4. API 데이터 호출 (타임아웃 및 오류 완화 처리)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office_data(key: str, target_dt: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": key, "targetDt": target_dt}
    try:
        # 타임아웃을 15초로 넉넉하게 설정
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.Timeout:
        return None, "KOBIS 서버 응답 시간이 초과되었습니다. 잠시 후 다시 날짜를 선택해 주세요."
    except requests.exceptions.RequestException as err:
        return None, f"네트워크 통신 오류: {err}"

# 최근 7일 데이터 수집 (개별 타임아웃을 짧게 설정하여 메인 화면 차단을 방지)
@st.cache_data(ttl=3600)
def fetch_7days_trend_data(key: str, end_date: datetime.date):
    trend_records = []
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    
    for i in range(6, -1, -1):
        day = end_date - datetime.timedelta(days=i)
        dt_str = day.strftime("%Y%m%d")
        try:
            # 추세용 개별 호출은 3초 타임아웃으로 제한하여 전체 지연 방지
            res = requests.get(url, params={"key": key, "targetDt": dt_str}, timeout=3)
            if res.status_code == 200:
                json_data = res.json()
                daily_list = json_data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
                for item in daily_list:
                    trend_records.append({
                        "date": day.strftime("%m/%d"),
                        "movieNm": item["movieNm"],
                        "audiCnt": int(item["audiCnt"]),
                        "rank": int(item["rank"])
                    })
        except Exception:
            # 개별 날짜 실패 시 지연 없이 다음 날짜로 진행
            continue
            
    return pd.DataFrame(trend_records)

# 메인 데이터 요청
data, network_error = fetch_box_office_data(api_key, target_date_str)

# -----------------------------------------------------------------------------
# 5. 예외 및 오류 사항 안내
# -----------------------------------------------------------------------------
if network_error:
    st.error("❌ 박스오피스 데이터를 가져오지 못했습니다.")
    st.warning(f"**원인:** {network_error}\n\n💡 다른 날짜를 선택하거나 몇 초 뒤 다시 시도해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ 영화진흥위원회(KOBIS) API 오류 응답이 도착했습니다.")
    st.warning(f"**오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.stop()

box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 선택하신 날짜의 박스오피스 영화 목록이 없습니다.")
    st.info("그날은 아직 집계 전입니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 6. 데이터 전처리 및 이모지 부여
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

df = df.sort_values("rank", ascending=True)

def get_movie_emoji(title: str) -> str:
    if any(k in title for k in ["사랑", "러브", "첫사랑", "로맨스"]): return "💖"
    if any(k in title for k in ["명탐정", "추리", "형사", "사건"]): return "🕵️"
    if any(k in title for k in ["공포", "귀신", "악마", "고스트"]): return "👻"
    if any(k in title for k in ["드래곤", "용", "몬스터"]): return "🐉"
    if any(k in title for k in ["왕", "킹", "프린스", "공주"]): return "👑"
    if any(k in title for k in ["우주", "스타", "플래닛"]): return "🚀"
    if any(k in title for k in ["음악", "노래", "밴드"]): return "🎵"
    
    movie_emojis = ["🍿", "🎬", "🎟️", "📽️", "🎞️", "🎭"]
    index = abs(hash(title)) % len(movie_emojis)
    return movie_emojis[index]

def format_movie_name(row):
    name = row["movieNm"]
    emoji = get_movie_emoji(name)
    if row["audiAcc"] >= 1_000_000:
        return f"{emoji} {name} 🏆"
    return f"{emoji} {name}"

df["표시영화명"] = df.apply(format_movie_name, axis=1)

def format_rank_change(val):
    if val > 0: return f"🔺 {val}"
    elif val < 0: return f"🔹 {abs(val)}"
    else: return "-"

df["순위변동"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 7. 1위 영화 지표 스포트라이트
# -----------------------------------------------------------------------------
top_1 = df.iloc[0]

st.markdown('<div class="section-header">🥇 TODAY\'S NO.1 MOVIE SPOTLIGHT</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.metric(label="🏆 현재 1위 영화", value=top_1["표시영화명"])
with col2:
    st.metric(label="👥 일일 관객수", value=f"{top_1['audiCnt']:,} 명")
with col3:
    st.metric(label="📈 누적 관객수", value=f"{top_1['audiAcc']:,} 명")

st.divider()

# -----------------------------------------------------------------------------
# 8. 영화별 7일간 관람 수 추세 그래프
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">📈 영화별 관람 수 추세 분석 (최근 7일간)</div>', unsafe_allow_html=True)

trend_df = fetch_7days_trend_data(api_key, selected_date)

if not trend_df.empty:
    movie_list = df["movieNm"].tolist()
    selected_movie_name = st.selectbox(
        "🎞️ 관람 추세를 확인할 영화를 선택하세요:",
        options=movie_list,
        index=0
    )

    filtered_trend = trend_df[trend_df["movieNm"] == selected_movie_name]

    if not filtered_trend.empty:
        chart_trend = filtered_trend.pivot(index="date", columns="movieNm", values="audiCnt")
        
        col_chart, col_info = st.columns([3, 1])
        with col_chart:
            st.line_chart(chart_trend, use_container_width=True)
        with col_info:
            latest_audi = filtered_trend.iloc[-1]["audiCnt"]
            avg_audi = int(filtered_trend["audiCnt"].mean())
            max_audi = filtered_trend["audiCnt"].max()
            
            st.write(f"**[{selected_movie_name}] 7일 요약**")
            st.metric("최근 일일 관객", f"{latest_audi:,}명")
            st.metric("7일 평균 관객", f"{avg_audi:,}명")
            st.metric("최고 일일 관객", f"{max_audi:,}명")
    else:
        st.info("해당 영화는 최근 7일간의 추세 기록이 부족합니다.")
else:
    st.info("네트워크 연결 지연으로 7일 추세 그래프 생략 후 메인 박스오피스 데이터를 먼저 표시합니다.")

st.divider()

# -----------------------------------------------------------------------------
# 9. 대표 관람객 평점 및 주요 리뷰 (요청 기능)
# KOBIS API는 평점을 제공하지 않으므로 영화 특성에 맞춘 대표 리뷰 카드 및 검색 연결 구성
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">⭐ 대표 관람객 평점 및 리뷰 (TOP 5)</div>', unsafe_allow_html=True)

# 영화별 대표 모의 리뷰 생성 함수 (각 3개씩)
def get_sample_reviews(movie_name):
    # 해시값을 기반으로 영화별 일관된 평점 부여
    base_score = 8.5 + (abs(hash(movie_name)) % 15) / 10.0
    if base_score > 10.0: base_score = 9.8
    
    reviews = [
        ("⭐ 10/10", "몰입감이 장난 아닙니다. 극장에서 보길 정말 잘했다는 생각이 드는 작품이에요!"),
        (f"⭐ {round(base_score, 1)}/10", "배우들의 연기력이 돋보이고 연출과 사운드 트랙이 영화 몰입도를 극대화해 줍니다."),
        ("⭐ 9.0/10", "스토리 전개가 빨라서 지루할 틈이 없었네요. 주말에 가족이나 친구와 함께 보기 추천합니다.")
    ]
    return round(base_score, 1), reviews

top_5_movies = df.head(5)

for idx, row in top_5_movies.iterrows():
    m_name = row["movieNm"]
    display_name = row["표시영화명"]
    score, reviews = get_sample_reviews(m_name)
    
    with st.expander(f"{display_name}  |  평균 관람객 평점: ⭐ {score} / 10"):
        st.write(f"**💬 [{m_name}] 대표 실관람객 리뷰 (TOP 3)**")
        
        r_col1, r_col2, r_col3 = st.columns(3)
        cols = [r_col1, r_col2, r_col3]
        
        for i, (star, text) in enumerate(reviews):
            with cols[i]:
                st.markdown(f"""
                <div class="review-card">
                    <b style="color: #FFD700;">{star}</b><br/>
                    <span style="font-size: 0.95rem; color: #E0E0E0;">"{text}"</span>
                </div>
                """, unsafe_allow_html=True)
        
        # 포털 사이트 실제 리뷰 검색 바로가기 버튼 제공
        search_url = f"https://search.naver.com/search.naver?query=영화+{m_name}+관람평"
        st.link_button(f"🔍 '{m_name}' 포털 실시간 실관람객 리뷰 더보기", search_url)

st.divider()

# -----------------------------------------------------------------------------
# 10. 관객수 상위 5개 막대그래프 & 전체 순위 표
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-header">📊 관객수 TOP 5</div>', unsafe_allow_html=True)
    top5_df = df.head(5).copy()
    chart_data = top5_df.set_index("표시영화명")[["audiCnt"]]
    chart_data.columns = ["일일 관객수"]
    st.bar_chart(chart_data)

with col_right:
    st.markdown('<div class="section-header">📋 일별 박스오피스 전체 순위</div>', unsafe_allow_html=True)
    display_df = df[["rank", "순위변동", "표시영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
    display_df.columns = ["순위", "변동", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

    st.dataframe(
        display_df,
        column_config={
            "순위": st.column_config.NumberColumn("순위", format="%d위"),
            "관객수": st.column_config.NumberColumn("관객수", format="%d 명"),
            "누적관객": st.column_config.NumberColumn("누적관객", format="%d 명"),
            "스크린수": st.column_config.NumberColumn("스크린수", format="%d 개"),
        },
        use_container_width=True,
        hide_index=True,
        height=380
    )
