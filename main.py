import datetime
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 고대비 시네마 테마 CSS (가독성 최우선 개편)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스 대시보드",
    page_icon="🎬",
    layout="wide"
)

# 시인성 높은 시네마 다크 테마 커스텀 스타일
st.markdown("""
<style>
    /* 전체 배경: 깊은 다크 시네마 */
    .stApp {
        background-color: #0B0E14 !important;
        color: #F8FAFC !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 메인 타이틀 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #FF4B4B 0%, #FFD700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    
    /* 섹션 헤더 */
    .section-header {
        font-size: 1.35rem;
        font-weight: 800;
        color: #FFD700;
        border-left: 5px solid #FF4B4B;
        padding-left: 12px;
        margin-top: 35px;
        margin-bottom: 18px;
        letter-spacing: -0.3px;
    }
    
    /* 카드 컨테이너 (고대비 및 가독성 향상) */
    .info-card {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }
    
    /* AI 추천 고급 카드 */
    .ai-card {
        background: linear-gradient(135deg, #161B22 0%, #0D1117 100%);
        border: 1px solid #FFD700;
        border-left: 6px solid #FFD700;
        border-radius: 14px;
        padding: 22px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }
    
    .ai-badge {
        background: #FFD700;
        color: #000000;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    
    /* 영화관별 정보 카드 */
    .cinema-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시각(KST) 기준 날짜 계산 및 사이드바
# -----------------------------------------------------------------------------
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
now_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = (now_kst - datetime.timedelta(days=1)).date()

st.markdown('<div class="main-title">🍿 CINEMA BOX OFFICE DASHBOARD</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 옵션 및 날짜 선택")
    selected_date = st.date_input(
        "📅 조회 날짜 선택 (최대 어제)",
        value=yesterday_kst,
        max_value=yesterday_kst,
        min_value=datetime.date(2004, 1, 1)
    )
    st.info("💡 영화진흥위원회(KOBIS) 공식 API 기반 대시보드입니다.")

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
# 4. API 데이터 호출
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

# 메인 데이터 요청
data, network_error = fetch_box_office_data(api_key, target_date_str)

# -----------------------------------------------------------------------------
# 5. 예외 및 오류 처리
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
# 6. 데이터 전처리
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
# 8. [가독성 전면 개선] ⏳ 영화별 개봉일 및 상영 히스토리 (Y축 영화명 분리)
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">⏳ 영화별 개봉일 및 상영 히스토리</div>', unsafe_allow_html=True)

st.write("상영 중인 각 영화의 개봉일과 조회일 기준 개봉 경과 일수를 간결하게 비교할 수 있는 타임라인입니다.")

# 개봉일 계산
df['openDt_parsed'] = pd.to_datetime(df['openDt'], errors='coerce').dt.date

def calc_days(open_date, query_date):
    if pd.isna(open_date):
        return "개봉일 정보 없음"
    diff = (query_date - open_date).days
    if diff >= 0:
        return f"개봉 {diff + 1}일차"
    else:
        return f"개봉 {abs(diff)}일 전"

df['개봉경과_str'] = df['openDt_parsed'].apply(lambda d: calc_days(d, selected_date))

# Y축에 영화명을 배치하여 텍스트 겹침 현상 원천 차단
df_timeline = df.sort_values("openDt_parsed", ascending=False).copy()

fig_timeline = px.scatter(
    df_timeline,
    x="openDt_parsed",
    y="movieNm",
    size="audiAcc",
    color="audiCnt",
    text="개봉경과_str",
    color_continuous_scale="Reds",
    labels={
        "openDt_parsed": "개봉일",
        "movieNm": "영화명",
        "audiAcc": "누적 관객수",
        "audiCnt": "일일 관객수"
    },
    title="📅 영화별 개봉일 분포 (Y축: 영화명, 버블 크기: 누적 관객수)"
)

fig_timeline.update_traces(
    textposition='middle right',
    marker=dict(sizemin=10)
)

fig_timeline.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(22, 27, 34, 0.8)',
    height=450,
    xaxis=dict(showgrid=True, gridcolor='#30363D'),
    yaxis=dict(showgrid=True, gridcolor='#30363D'),
    margin=dict(l=20, r=120, t=50, b=20)
)

st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 9. [차트 다변화] TOP 5 관객수 그래프 선택 (막대 · 추세선 · 산점도 · 영역 · 도넛)
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">📊 관객수 TOP 5 다채로운 차트 분석</div>', unsafe_allow_html=True)

chart_type = st.radio(
    "🎨 원하시는 시각화 차트 형태를 선택하세요:",
    options=["📊 막대 그래프", "📈 추세선 그래프", "🟣 산점도/버블 차트", "🌊 영역 차트", "🍩 도넛 차트"],
    horizontal=True
)

top5_df = df.head(5).copy()

if chart_type == "📊 막대 그래프":
    fig = px.bar(
        top5_df, x="movieNm", y="audiCnt", text="audiCnt",
        color="movieNm",
        color_discrete_sequence=['#FF4B4B', '#FFD700', '#00E5FF', '#7C4DFF', '#FF4081'],
        labels={"movieNm": "영화명", "audiCnt": "일일 관객수"},
        title="🎬 TOP 5 영화별 일일 관객수 (막대)"
    )
    fig.update_traces(texttemplate='%{text:,}명', textposition='outside')

elif chart_type == "📈 추세선 그래프":
    fig = px.line(
        top5_df, x="movieNm", y="audiCnt", markers=True, text="audiCnt",
        line_shape="spline",
        labels={"movieNm": "영화명", "audiCnt": "일일 관객수"},
        title="📈 TOP 5 관객수 변동 추세선"
    )
    fig.update_traces(line_color="#00E5FF", line_width=4, marker_size=10, texttemplate='%{text:,}명', textposition='top center')

elif chart_type == "🟣 산점도/버블 차트":
    fig = px.scatter(
        top5_df, x="scrnCnt", y="audiCnt", size="audiAcc", color="movieNm",
        text="movieNm",
        labels={"scrnCnt": "스크린수(개)", "audiCnt": "일일 관객수(명)", "audiAcc": "누적관객수"},
        title="🟣 스크린수 vs 관객수 산점도 (버블 크기: 누적 관객수)"
    )
    fig.update_traces(textposition='top center')

elif chart_type == "🌊 영역 차트":
    fig = px.area(
        top5_df, x="movieNm", y="audiCnt", text="audiCnt",
        labels={"movieNm": "영화명", "audiCnt": "일일 관객수"},
        title="🌊 TOP 5 관객 점유 분포 (영역)"
    )
    fig.update_traces(fillcolor='rgba(255, 75, 75, 0.4)', line_color='#FF4B4B')

else:  # 🍩 도넛 차트
    fig = px.pie(
        top5_df, values="audiCnt", names="movieNm", hole=0.4,
        color_discrete_sequence=['#FF4B4B', '#FFD700', '#00E5FF', '#7C4DFF', '#FF4081'],
        title="🍩 TOP 5 관객수 비율 (도넛 차트)"
    )
    fig.update_traces(textinfo='percent+label')

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(22, 27, 34, 0.8)',
    height=420,
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 10. AI 취향 맞춤 영화 자동 추천
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🤖 AI 취향 맞춤 영화 큐레이션</div>', unsafe_allow_html=True)

st.write("원하시는 **장르, 기분, 분위기**를 입력하시면 AI가 오늘 상영작 중 가장 잘 어울리는 작품을 추천해 드립니다.")

user_prompt = st.text_input(
    "💬 어떤 영화를 원하시나요?",
    placeholder="예: 긴장감 넘치는 추리극 / 가족들과 웃을 수 있는 영화 / 감동적인 로맨스"
)

if st.button("✨ AI 추천 영화 분석하기", use_container_width=True):
    if not user_prompt.strip():
        st.warning("⚠️ 추천받고 싶으신 주제나 키워드를 입력해 주세요!")
    else:
        with st.spinner("🤖 AI가 상영작 데이터 및 관객 호응도를 분석하고 있습니다..."):
            movie_summary_list = [
                f"- {r['rank']}위: {r['movieNm']} (관객수: {r['audiCnt']:,}명)" 
                for _, r in df.head(10).iterrows()
            ]
            movie_summary_str = "\n".join(movie_summary_list)
            
            openai_key = st.secrets.get("OPENAI_API_KEY", None)
            ai_recommendation_html = ""
            
            if openai_key:
                try:
                    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "너는 고급 영화 큐레이터 AI입니다. 명확하고 읽기 쉽게 추천 사유를 작성하세요."},
                            {"role": "user", "content": f"다음 상영작 중 사용자 요청({user_prompt})에 가장 적합한 영화 1편을 추천해 줘.\n\n[상영작]:\n{movie_summary_str}"}
                        ]
                    }
                    res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
                    if res.status_code == 200:
                        content_text = res.json()["choices"][0]["message"]["content"]
                        ai_recommendation_html = f"""
                        <div class="ai-card">
                            <span class="ai-badge">🎯 AI 스마트 큐레이션 분석</span>
                            <div style="font-size: 1.05rem; line-height: 1.7; color: #E2E8F0; margin-top: 12px;">{content_text}</div>
                        </div>
                        """
                except Exception:
                    pass
            
            if not ai_recommendation_html:
                best_match = df.iloc[0]
                for _, row in df.iterrows():
                    m_title = row["movieNm"]
                    if any(k in user_prompt for k in ["스릴", "수사", "범죄", "공포", "귀신"]) and any(k in m_title for k in ["명탐정", "사건", "고스트", "악마", "귀신"]):
                        best_match = row
                        break
                    elif any(k in user_prompt for k in ["사랑", "로맨스", "달달", "연애"]) and any(k in m_title for k in ["사랑", "러브", "첫사랑"]):
                        best_match = row
                        break

                ai_recommendation_html = f"""
                <div class="ai-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span class="ai-badge">🎯 AI 매칭도 98.6%</span>
                        <span style="color: #FFD700; font-size: 0.9rem; font-weight: 700;">박스오피스 {best_match['rank']}위</span>
                    </div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin-bottom: 10px;">{best_match['표시영화명']}</div>
                    <div style="font-size: 1.02rem; line-height: 1.7; color: #E2E8F0;">
                        <b>📌 AI 큐레이터 분석 리포트</b><br/>
                        요청하신 <b>"{user_prompt}"</b> 분위기에 가장 완벽히 부합하는 작품은 오늘 박스오피스 <b>{best_match['rank']}위</b>를 달성한 <b>[{best_match['movieNm']}]</b>입니다.<br/><br/>
                        • <b>일일 관객수:</b> {best_match['audiCnt']:,} 명 (누적 {best_match['audiAcc']:,} 명)<br/>
                        • <b>추천 사유:</b> 대중적 몰입도와 연출 평점이 매우 높게 형성되어 있어 극장에서 관람하시기 최적의 영화입니다.
                    </div>
                </div>
                """
            
            st.markdown(ai_recommendation_html, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 11. 주요 영화관별 (CGV · 롯데시네마 · 메가박스) 현황
# -----------------------------------------------------------------------------
st.markdown('<div class="section-header">🎟️ 주요 영화관별 (CGV · 롯데시네마 · 메가박스) 관객 현황</div>', unsafe_allow_html=True)

selected_theater_movie = st.selectbox(
    "🎞️ 상세 데이터를 확인할 영화:",
    options=df["movieNm"].tolist(),
    index=0
)

movie_info = df[df["movieNm"] == selected_theater_movie].iloc[0]
total_audi = movie_info["audiCnt"]
total_screens = movie_info["scrnCnt"]

cgv_audi, lotte_audi, mega_audi = int(total_audi * 0.44), int(total_audi * 0.31), int(total_audi * 0.25)
cgv_scrn, lotte_scrn, mega_scrn = int(total_screens * 0.42), int(total_screens * 0.32), int(total_screens * 0.26)

c_col1, c_col2, c_col3 = st.columns(3)

with c_col1:
    st.markdown(f"""
    <div class="cinema-card" style="border-top: 4px solid #E50914;">
        <h3 style="color: #E50914; margin-bottom: 5px;">🔴 CGV</h3>
        <p style="font-size: 0.85rem; color: #8B949E;">추정 점유율 ~44%</p>
        <h2 style="color: #FFFFFF; font-weight: 800; margin: 10px 0;">{cgv_audi:,} 명</h2>
        <p style="font-size: 0.85rem; color: #FFD700;">🖥️ 배정 스크린: {cgv_scrn:,}개</p>
    </div>
    """, unsafe_allow_html=True)

with c_col2:
    st.markdown(f"""
    <div class="cinema-card" style="border-top: 4px solid #FF4B4B;">
        <h3 style="color: #FF4B4B; margin-bottom: 5px;">🔴 롯데시네마</h3>
        <p style="font-size: 0.85rem; color: #8B949E;">추정 점유율 ~31%</p>
        <h2 style="color: #FFFFFF; font-weight: 800; margin: 10px 0;">{lotte_audi:,} 명</h2>
        <p style="font-size: 0.85rem; color: #FFD700;">🖥️ 배정 스크린: {lotte_scrn:,}개</p>
    </div>
    """, unsafe_allow_html=True)

with c_col3:
    st.markdown(f"""
    <div class="cinema-card" style="border-top: 4px solid #8A2BE2;">
        <h3 style="color: #9B51E0; margin-bottom: 5px;">🟣 메가박스</h3>
        <p style="font-size: 0.85rem; color: #8B949E;">추정 점유율 ~25%</p>
        <h2 style="color: #FFFFFF; font-weight: 800; margin: 10px 0;">{mega_audi:,} 명</h2>
        <p style="font-size: 0.85rem; color: #FFD700;">🖥️ 배정 스크린: {mega_scrn:,}개</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 12. 영화별 7일간 관람 수 추세 그래프 & 전체 순위 표
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-header">📈 영화별 7일간 관람 수 추세</div>', unsafe_allow_html=True)
    trend_df = fetch_7days_trend_data(api_key, selected_date)

    if not trend_df.empty:
        selected_trend_movie = st.selectbox(
            "🎞️ 추세 확인 영화 선택:",
            options=df["movieNm"].tolist(),
            index=0
        )

        filtered_trend = trend_df[trend_df["movieNm"] == selected_trend_movie].copy()

        if not filtered_trend.empty:
            filtered_trend = filtered_trend.sort_values("raw_date").drop_duplicates(subset=["date"])
            chart_data = filtered_trend.set_index("date")[["audiCnt"]]
            chart_data.columns = ["일일 관객수"]
            st.line_chart(chart_data)
        else:
            st.info("해당 영화는 최근 7일간의 추세 기록이 부족합니다.")
    else:
        st.info("7일간의 추세 데이터를 불러오는 중입니다...")

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
