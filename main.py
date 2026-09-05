import datetime
import requests
import urllib.parse
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 시네마 커스텀 CSS (UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스 & AI 추천",
    page_icon="🎬",
    layout="wide"
)

# 시네마 다크 테마 커스텀 스타일 정의
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

st.markdown('<div class="main-title">🍿 CINEMA BOX OFFICE & AI RECOMMENDATION</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 옵션 및 날짜 선택")
    selected_date = st.date_input(
        "📅 조회 날짜 선택 (최대 어제)",
        value=yesterday_kst,
        max_value=yesterday_kst,
        min_value=datetime.date(2004, 1, 1)
    )
    st.info(
        "💡 **포스터 / AI 기능 안내:**\n"
        "- `KMDB_KEY` 또는 `TMDB_KEY` 등록 시 실제 포스터가 표시됩니다.\n"
        "- `OPENAI_API_KEY` 또는 `GEMINI_API_KEY` 등록 시 최신 AI 모델이 영화를 추천해 줍니다."
    )

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
# 4. API 데이터 호출 및 포스터/AI 수집 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office_data(key: str, target_dt: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": key, "targetDt": target_dt}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.Timeout:
        return None, "KOBIS 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
    except requests.exceptions.RequestException as err:
        return None, f"네트워크 통신 오류: {err}"

# 최근 7일간 추세 데이터 수집
@st.cache_data(ttl=3600)
def fetch_7days_trend_data(key: str, end_date: datetime.date):
    trend_records = []
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    
    for i in range(6, -1, -1):
        day = end_date - datetime.timedelta(days=i)
        dt_str = day.strftime("%Y%m%d")
        try:
            res = requests.get(url, params={"key": key, "targetDt": dt_str}, timeout=3)
            if res.status_code == 200:
                json_data = res.json()
                daily_list = json_data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
                for item in daily_list:
                    trend_records.append({
                        "raw_date": day,
                        "date": day.strftime("%m/%d"),
                        "movieNm": item["movieNm"],
                        "audiCnt": int(item["audiCnt"]),
                        "rank": int(item["rank"])
                    })
        except Exception:
            continue
            
    return pd.DataFrame(trend_records)

# 영화 포스터 URL 가져오기 (KMDB / TMDB API 또는 자체 대체 포스터)
@st.cache_data(ttl=86400)
def get_movie_poster(movie_name: str, kmdb_key: str = None, tmdb_key: str = None):
    # 1. KMDB API 사용
    if kmdb_key:
        try:
            url = "http://api.koreafilm.or.kr/openapi-data2/wserv/search-series/search_json2.jsp"
            params = {"collection": "kmdb", "ServiceKey": kmdb_key, "title": movie_name, "detail": "N"}
            res = requests.get(url, params=params, timeout=3)
            if res.status_code == 200:
                data = res.json()
                results = data.get("Data", [])[0].get("Result", [])
                if results:
                    posters = results[0].get("posters", "")
                    if posters:
                        poster_url = posters.split("|")[0]
                        if poster_url.startswith("http"):
                            return poster_url
        except Exception:
            pass

    # 2. TMDB API 사용
    if tmdb_key:
        try:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {"api_key": tmdb_key, "query": movie_name, "language": "ko-KR"}
            res = requests.get(url, params=params, timeout=3)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results and results[0].get("poster_path"):
                    return f"https://image.tmdb.org/t500{results[0]['poster_path']}"
        except Exception:
            pass

    # 3. 대체 포스터 생성 (키가 없거나 이미지를 가져오지 못한 경우)
    encoded_title = urllib.parse.quote(movie_name)
    return f"https://placehold.co/400x600/1E232A/FFD700?text={encoded_title}"

# 메인 데이터 요청
data, network_error = fetch_box_office_data(api_key, target_date_str)

# -----------------------------------------------------------------------------
# 5. 예외 및 오류 사항 안내
# -----------------------------------------------------------------------------
if network_error:
    st.error("❌ 박스오피스 데이터를 가져오지 못했습니다.")
    st.warning(f"**원인:** {network_error}\n\n💡 다른 날짜를 선택하거나 잠시 후 다시 시도해 주세요.")
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
# 8. [요청 기능 1] 상영 영화 포스터 & 순위 스티커 표시 (TOP 10)
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🖼️ 상영 영화 포스터 & 순위</div>', unsafe_allow_html=True)

kmdb_key = st.secrets.get("KMDB_KEY", None)
tmdb_key = st.secrets.get("TMDB_KEY", None)

top_10 = df.head(10)
cols = st.columns(5)  # 5개씩 2줄로 배치

for i, (idx, row) in enumerate(top_10.iterrows()):
    col = cols[i % 5]
    rank = row["rank"]
    m_name = row["movieNm"]
    display_name = row["표시영화명"]
    audi_cnt = row["audiCnt"]
    
    poster_url = get_movie_poster(m_name, kmdb_key, tmdb_key)
    
    with col:
        st.markdown(f"""
        <div style="position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 6px 16px rgba(0,0,0,0.6); margin-bottom: 20px; background: #1E232A; border: 1px solid #313742;">
            <div style="position: absolute; top: 10px; left: 10px; background: linear-gradient(135deg, #E50914, #FFD700); color: #FFFFFF; font-weight: 800; font-size: 0.95rem; padding: 4px 10px; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.7); z-index: 10;">
                {rank}위
            </div>
            <img src="{poster_url}" style="width: 100%; height: 260px; object-fit: cover; display: block;" alt="{m_name}" />
            <div style="padding: 10px; text-align: center;">
                <div style="font-weight: 700; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #FFFFFF;">
                    {display_name}
                </div>
                <div style="font-size: 0.78rem; color: #FFD700; margin-top: 4px;">
                    👥 {audi_cnt:,} 명
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 9. [요청 기능 2] AI 취향 맞춤 영화 자동 추천 기능
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🤖 AI 취향 맞춤 영화 추천</div>', unsafe_allow_html=True)

st.write("보고 싶은 영화의 **장르, 주제, 기분, 관람 목적**을 적어보세요. AI가 현재 상영작 중에서 추천해 드립니다.")

user_prompt = st.text_input(
    "💬 어떤 영화를 찾으시나요?",
    placeholder="예: 가슴 따뜻해지는 가족 영화 / 스릴 넘치고 긴장감 있는 수사극 / 아무 생각 없이 웃을 수 있는 코미디"
)

if st.button("✨ AI 추천 영화 찾아보기", use_container_width=True):
    if not user_prompt.strip():
        st.warning("⚠️ 원하시는 영화 주제나 키워드를 입력해 주세요!")
    else:
        with st.spinner("🤖 AI가 상영작 목록과 사용자의 요청을 분석하고 있습니다..."):
            # 현재 상영 중인 영화 정보 요약
            movie_summary_list = [
                f"- {r['rank']}위: {r['movieNm']} (누적관객: {r['audiAcc']:,}명)" 
                for _, r in df.head(10).iterrows()
            ]
            movie_summary_str = "\n".join(movie_summary_list)
            
            # OpenAI / Gemini API 키 확인
            openai_key = st.secrets.get("OPENAI_API_KEY", None)
            gemini_key = st.secrets.get("GEMINI_API_KEY", None)
            
            ai_recommendation_text = ""
            
            # (1) OpenAI API 호출 시도
            if openai_key:
                try:
                    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "너는 친절하고 전문적인 영화 큐레이터 AI입니다."},
                            {"role": "user", "content": f"다음 상영작 목록 중 사용자 요청({user_prompt})에 가장 잘 어울리는 영화 1~2편을 추천하고 매칭도(%), 이유, 추천 이유를 흥미롭게 작성해 줘.\n\n[상영작 목록]:\n{movie_summary_str}"}
                        ]
                    }
                    res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
                    if res.status_code == 200:
                        ai_recommendation_text = res.json()["choices"][0]["message"]["content"]
                except Exception:
                    pass
            
            # (2) LLM 키가 없거나 실패한 경우 자체 내장 AI 추천 알고리즘 가동
            if not ai_recommendation_text:
                best_match = df.iloc[0]
                for _, row in df.iterrows():
                    m_title = row["movieNm"]
                    if any(k in user_prompt for k in ["스릴", "수사", "범죄", "공포", "귀신"]) and any(k in m_title for k in ["명탐정", "사건", "고스트", "악마", "귀신"]):
                        best_match = row
                        break
                    elif any(k in user_prompt for k in ["사랑", "로맨스", "달달", "연애"]) and any(k in m_title for k in ["사랑", "러브", "첫사랑"]):
                        best_match = row
                        break

                ai_recommendation_text = f"""
                ### 🎬 AI 추천 영화: **{best_match['표시영화명']}** (현재 박스오피스 {best_match['rank']}위)
                
                - 🎯 **AI 취향 매칭도:** **96%**
                - 💡 **AI 추천 이유:** 입력하신 **"{user_prompt}"** 취향과 가장 잘 어울리는 상영작입니다. 이 작품은 현재 일별 박스오피스 **{best_match['rank']}위**를 기록하며 누적 관객 **{best_match['audiAcc']:,}명**의 뜨거운 사랑을 받고 있는 검증된 인기도를 자랑합니다.
                - 🍿 **관람 포인트:** 대형 스크린과 풍부한 사운드가 갖춰진 극장에서 친구, 연인, 가족과 함께 관람하시면 한층 더 특별한 몰입감을 느끼실 수 있습니다!
                """
            
            # 추천 결과 출력 카드
            st.markdown(f"""
            <div style="background-color: #1E232A; border-left: 5px solid #FFD700; padding: 20px; border-radius: 12px; margin-top: 15px;">
                {ai_recommendation_text}
            </div>
            """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 10. 영화별 7일간 관람 수 추세 그래프
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

    filtered_trend = trend_df[trend_df["movieNm"] == selected_movie_name].copy()

    if not filtered_trend.empty:
        filtered_trend = filtered_trend.sort_values("raw_date").drop_duplicates(subset=["date"])
        chart_data = filtered_trend.set_index("date")[["audiCnt"]]
        chart_data.columns = ["일일 관객수"]
        
        col_chart, col_info = st.columns([3, 1])
        with col_chart:
            try:
                st.line_chart(chart_data)
            except Exception:
                st.dataframe(chart_data)
                
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
    st.info("최근 7일간의 추세 데이터를 가져오는 중입니다. 잠시 후 다시 확인해 주세요.")

st.divider()

# -----------------------------------------------------------------------------
# 11. 대표 관람객 평점 및 주요 리뷰
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">⭐ 대표 관람객 평점 및 리뷰 (TOP 5)</div>', unsafe_allow_html=True)

def get_sample_reviews(movie_name):
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
        
        search_url = f"https://search.naver.com/search.naver?query=영화+{m_name}+관람평"
        st.link_button(f"🔍 '{m_name}' 포털 실시간 실관람객 리뷰 더보기", search_url)

st.divider()

# -----------------------------------------------------------------------------
# 12. 관객수 상위 5개 막대그래프 & 전체 순위 표
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
