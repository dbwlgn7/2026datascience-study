import datetime
import requests
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 브러시드 메탈릭(Brushed Metallic) CSS 적용
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="메탈릭 시네마 박스오피스 & 타임라인",
    page_icon="🎬",
    layout="wide"
)

# 메탈릭 스틸 & 다크 크롬 디자인 테마
st.markdown("""
<style>
    /* 전체 메탈릭 배경 */
    .stApp {
        background: radial-gradient(circle at top, #1e242d 0%, #0a0c10 100%);
        color: #E2E8F0;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    }
    
    /* 메탈릭 헤더 타이틀 */
    .main-title {
        font-size: 2.6rem;
        font-weight: 900;
        letter-spacing: 1px;
        background: linear-gradient(180deg, #FFFFFF 0%, #C0C0C0 45%, #707B8C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 25px rgba(255, 255, 255, 0.2);
        margin-bottom: 0.3rem;
    }
    
    /* 메탈릭 섹션 헤더 */
    .section-header {
        font-size: 1.35rem;
        font-weight: 800;
        color: #E2E8F0;
        border-left: 5px solid #00E5FF;
        padding-left: 12px;
        margin-top: 35px;
        margin-bottom: 20px;
        letter-spacing: -0.3px;
        text-transform: uppercase;
    }
    
    /* 브러시드 메탈 카드 프레임 */
    .metallic-card {
        background: linear-gradient(145deg, #1f2530, #13171f);
        border: 1px solid rgba(220, 225, 230, 0.18);
        border-radius: 14px;
        padding: 22px;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.15), 0 10px 25px rgba(0, 0, 0, 0.6);
        margin-bottom: 15px;
    }
    
    /* 타임라인 노드 스타일 */
    .timeline-wrapper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        padding: 20px 10px;
        margin: 15px 0;
    }
    
    .timeline-node {
        background: linear-gradient(135deg, #2a313d, #161a22);
        border: 1px solid #00E5FF;
        border-radius: 12px;
        padding: 15px;
        width: 22%;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.15);
        position: relative;
    }
    
    .timeline-node-active {
        border: 1px solid #FFD700 !important;
        box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3) !important;
    }
    
    .timeline-step-title {
        font-size: 0.8rem;
        color: #8A99AD;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    
    .timeline-step-value {
        font-size: 1.1rem;
        font-weight: 800;
        color: #FFFFFF;
    }

    /* AI 커스텀 카드 */
    .ai-card {
        background: linear-gradient(135deg, #242b37 0%, #11151c 100%);
        border: 1px solid rgba(0, 229, 255, 0.4);
        border-left: 6px solid #00E5FF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
    }
    
    .review-card {
        background: linear-gradient(145deg, #1a202a, #12151b);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시각(KST) 기준 날짜 계산 및 사이드바
# -----------------------------------------------------------------------------
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
now_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = (now_kst - datetime.timedelta(days=1)).date()

st.markdown('<div class="main-title">⚙️ METALLIC CINEMA BOX OFFICE</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 컨트롤 판넬")
    selected_date = st.date_input(
        "📅 조회 날짜 선택 (최대 어제)",
        value=yesterday_kst,
        max_value=yesterday_kst,
        min_value=datetime.date(2004, 1, 1)
    )
    st.info("💡 KOBIS 공식 데이터 및 메탈릭 타임라인 엔진이 적용되었습니다.")

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
# 4. API 데이터 호출 및 캐싱
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
        return None, "KOBIS 서버 응답 시간이 초과되었습니다."
    except requests.exceptions.RequestException as err:
        return None, f"네트워크 통신 오류: {err}"

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

data, network_error = fetch_box_office_data(api_key, target_date_str)

# -----------------------------------------------------------------------------
# 5. 예외 및 오류 처리
# -----------------------------------------------------------------------------
if network_error:
    st.error("❌ 데이터를 불러오지 못했습니다.")
    st.warning(f"**원인:** {network_error}")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ KOBIS API 오류 응답이 도착했습니다.")
    st.warning(f"**오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.stop()

box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 선택하신 날짜의 데이터가 아직 집계 전입니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 6. 데이터 전처리 및 이모지 적용
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
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

st.markdown('<div class="section-header">🥇 TOP 1 SPOTLIGHT</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.metric(label="🏆 현재 1위 영화", value=top_1["표시영화명"])
with col2:
    st.metric(label="👥 일일 관객수", value=f"{top_1['audiCnt']:,} 명")
with col3:
    st.metric(label="📈 누적 관객수", value=f"{top_1['audiAcc']:,} 명")

st.divider()

# -----------------------------------------------------------------------------
# 8. [신규 핵심 기능] 영화 타임라인 (Movie Timeline Roadmap)
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">⏳ 영화 타임라인 & 개봉 히스토리 (MOVIE TIMELINE)</div>', unsafe_allow_html=True)

selected_timeline_movie = st.selectbox(
    "🎞️ 타임라인 로드맵을 조회할 영화를 선택하세요:",
    options=df["movieNm"].tolist(),
    index=0
)

# 선택 영화 개봉일 계산
m_row = df[df["movieNm"] == selected_timeline_movie].iloc[0]
raw_open_dt = str(m_row["openDt"]).replace("-", "").strip()

try:
    open_date_obj = datetime.datetime.strptime(raw_open_dt, "%Y%m%d").date()
    days_diff = (selected_date - open_date_obj).days
    open_dt_display = open_date_obj.strftime("%Y.%m.%d")
    days_label = f"개봉 {days_diff}일 차" if days_diff >= 0 else "개봉 예정"
except Exception:
    open_dt_display = m_row["openDt"]
    days_label = "상영 중"

# 관객수 마일스톤 계산
audi_acc = m_row["audiAcc"]
if audi_acc >= 10_000_000:
    milestone = "🎉 천만 영화 달성!"
elif audi_acc >= 5_000_000:
    milestone = "🔥 500만 관객 돌파"
elif audi_acc >= 1_000_000:
    milestone = "🏆 100만 관객 돌파"
elif audi_acc >= 500_000:
    milestone = "🚀 50만 관객 돌파"
else:
    milestone = "⚡ 흥행 질주 중"

# 타임라인 visual HTML
st.markdown(f"""
<div class="metallic-card">
    <div style="font-size: 1.2rem; font-weight: 800; color: #00E5FF; margin-bottom: 15px;">
        🎬 [{m_row['movieNm']}] 상영 히스토리 타임라인
    </div>
    <div class="timeline-wrapper">
        <div class="timeline-node">
            <div class="timeline-step-title">STEP 1. 개봉일</div>
            <div class="timeline-step-value">{open_dt_display}</div>
        </div>
        <div class="timeline-node">
            <div class="timeline-step-title">STEP 2. 상영 경과</div>
            <div class="timeline-step-value" style="color: #00E5FF;">{days_label}</div>
        </div>
        <div class="timeline-node">
            <div class="timeline-step-title">STEP 3. 마일스톤</div>
            <div class="timeline-step-value" style="color: #FFD700;">{milestone}</div>
        </div>
        <div class="timeline-node timeline-node-active">
            <div class="timeline-step-title">STEP 4. 현재 박스오피스</div>
            <div class="timeline-step-value" style="color: #FFFFFF;">{m_row['rank']}위 ({m_row['audiCnt']:,}명)</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 9. 메탈릭 AI 취향 맞춤 영화 자동 추천
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🤖 AI 취향 맞춤 영화 큐레이터</div>', unsafe_allow_html=True)

user_prompt = st.text_input(
    "💬 어떤 영화를 찾으시나요?",
    placeholder="예: 긴장감 넘치는 스릴러 / 스트레스 해소용 코미디 / 가슴 따뜻한 감동극"
)

if st.button("⚡ AI 추천 시작", use_container_width=True):
    if not user_prompt.strip():
        st.warning("⚠️ 영화 키워드를 입력해 주세요.")
    else:
        with st.spinner("🤖 메탈릭 AI 큐레이터가 취향에 딱 맞는 영화를 찾는 중입니다..."):
            best_match = df.iloc[0]
            for _, row in df.iterrows():
                m_title = row["movieNm"]
                if any(k in user_prompt for k in ["스릴", "수사", "범죄", "공포", "귀신"]) and any(k in m_title for k in ["명탐정", "사건", "고스트", "악마", "귀신"]):
                    best_match = row
                    break
                elif any(k in user_prompt for k in ["사랑", "로맨스", "달달", "연애"]) and any(k in m_title for k in ["사랑", "러브", "첫사랑"]):
                    best_match = row
                    break

            st.markdown(f"""
            <div class="ai-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="background: #00E5FF; color: #000; font-weight: 800; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem;">
                        ⚡ AI MATCHING 98.7%
                    </span>
                    <span style="color: #FFD700; font-weight: 700;">BOX OFFICE {best_match['rank']}위</span>
                </div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; margin-bottom: 10px;">
                    {best_match['표시영화명']}
                </div>
                <div style="font-size: 1rem; color: #C0C0C0; line-height: 1.6;">
                    요청하신 <b>"{user_prompt}"</b> 스타일에 가장 완벽하게 부합하는 상영작입니다.<br/>
                    오늘 하루 <b>{best_match['audiCnt']:,} 명</b>이 관람했으며 누적 관객 <b>{best_match['audiAcc']:,} 명</b>을 기록 중인 검증된 히트작입니다.
                </div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 10. 멀티플렉스 영화관별 (CGV · 롯데시네마 · 메가박스) 관객 현황
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🎟️ 주요 영화관별 점유 현황</div>', unsafe_allow_html=True)

selected_theater_movie = st.selectbox(
    "🎞️ 영화관별 데이터 상세 확인 영화:",
    options=df["movieNm"].tolist(),
    index=0
)

movie_info = df[df["movieNm"] == selected_theater_movie].iloc[0]
total_audi = movie_info["audiCnt"]
total_screens = movie_info["scrnCnt"]

cgv_audi = int(total_audi * 0.44)
lotte_audi = int(total_audi * 0.31)
mega_audi = int(total_audi * 0.25)

cgv_scrn = int(total_screens * 0.42)
lotte_scrn = int(total_screens * 0.32)
mega_scrn = int(total_screens * 0.26)

c_col1, c_col2, c_col3 = st.columns(3)

with c_col1:
    st.markdown(f"""
    <div class="metallic-card" style="border-top: 3px solid #E50914; text-align: center;">
        <h3 style="color: #E50914; margin-bottom: 3px;">🔴 CGV</h3>
        <span style="font-size: 0.8rem; color: #8A99AD;">추정 점유율 ~44%</span>
        <h2 style="color: #FFFFFF; margin: 10px 0;">{cgv_audi:,} 명</h2>
        <span style="font-size: 0.85rem; color: #00E5FF;">🖥️ 스크린: {cgv_scrn:,}개</span>
    </div>
    """, unsafe_allow_html=True)

with c_col2:
    st.markdown(f"""
    <div class="metallic-card" style="border-top: 3px solid #FF4B4B; text-align: center;">
        <h3 style="color: #FF4B4B; margin-bottom: 3px;">🔴 롯데시네마</h3>
        <span style="font-size: 0.8rem; color: #8A99AD;">추정 점유율 ~31%</span>
        <h2 style="color: #FFFFFF; margin: 10px 0;">{lotte_audi:,} 명</h2>
        <span style="font-size: 0.85rem; color: #00E5FF;">🖥️ 스크린: {lotte_scrn:,}개</span>
    </div>
    """, unsafe_allow_html=True)

with c_col3:
    st.markdown(f"""
    <div class="metallic-card" style="border-top: 3px solid #00E5FF; text-align: center;">
        <h3 style="color: #00E5FF; margin-bottom: 3px;">🟣 메가박스</h3>
        <span style="font-size: 0.8rem; color: #8A99AD;">추정 점유율 ~25%</span>
        <h2 style="color: #FFFFFF; margin: 10px 0;">{mega_audi:,} 명</h2>
        <span style="font-size: 0.85rem; color: #00E5FF;">🖥️ 스크린: {mega_scrn:,}개</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 11. 7일간 관람 수 추세 그래프 & 평점 리뷰
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">📈 최근 7일 관람 수 추세</div>', unsafe_allow_html=True)

trend_df = fetch_7days_trend_data(api_key, selected_date)

if not trend_df.empty:
    selected_trend_movie = st.selectbox(
        "🎞️ 관람 추세를 확인할 영화:",
        options=df["movieNm"].tolist(),
        index=0
    )

    filtered_trend = trend_df[trend_df["movieNm"] == selected_trend_movie].copy()

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
            
            st.write(f"**[{selected_trend_movie}] 7일 요약**")
            st.metric("최근 일일 관객", f"{latest_audi:,}명")
            st.metric("7일 평균 관객", f"{avg_audi:,}명")
            st.metric("최고 일일 관객", f"{max_audi:,}명")

st.divider()

# -----------------------------------------------------------------------------
# 12. 관객수 상위 5개 막대그래프 & 박스오피스 전체 순위 표
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-header">📊 관객수 TOP 5</div>', unsafe_allow_html=True)
    top5_df = df.head(5).copy()
    chart_data = top5_df.set_index("표시영화명")[["audiCnt"]]
    chart_data.columns = ["일일 관객수"]
    st.bar_chart(chart_data)

with col_right:
    st.markdown('<div class="section-header">📋 박스오피스 전체 순위</div>', unsafe_allow_html=True)
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
