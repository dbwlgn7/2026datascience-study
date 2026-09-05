import datetime
import requests
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 제목 표시
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="일별 박스오피스 조회",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스 조회")

# -----------------------------------------------------------------------------
# 2. 한국 시각(KST: UTC+9) 기준 '어제' 날짜 계산 및 달력 위젯 생성
# -----------------------------------------------------------------------------
# 배포 서버 시계(UTC)와 한국 시차(+9시간)를 반영하여 한국 시각의 '어제'를 구합니다.
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
now_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = (now_kst - datetime.timedelta(days=1)).date()

# 달력(Date Input)에서 사용자가 직접 날짜를 선택할 수 있게 합니다.
# 오늘 및 미래 날짜는 아직 데이터 집계 전이므로 선택 불가능(max_value=yesterday_kst)하도록 설정합니다.
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요 (최대 어제까지 선택 가능):",
    value=yesterday_kst,
    max_value=yesterday_kst,
    min_value=datetime.date(2004, 1, 1)  # KOBIS 데이터 제공 시작 시점
)

# API 요청용(YYYYMMDD)과 화면 표시용(YYYY년 MM월 DD일) 날짜 문자열 변환
target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.caption(f"📅 **조회 기준일:** {display_date_str}")

# -----------------------------------------------------------------------------
# 3. Streamlit Secrets에서 API 인증키 불러오기
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 인증키(KOBIS_KEY)가 비밀 금고(Secrets)에 등록되어 있지 않습니다.")
    st.info(
        "**확인 및 해결 방법:**\n"
        "1. **Streamlit Cloud 배포 화면:** App settings -> **Secrets** 메뉴로 이동합니다.\n"
        "2. 아래 형식으로 발급받은 인증키를 입력하고 저장해 주세요.\n"
        "   ```toml\n"
        '   KOBIS_KEY = "발급받은_인증키_입력"\n'
        "   ```\n"
        "3. **로컬 개발 환경:** 프로젝트 폴더 안 `.streamlit/secrets.toml` 파일에 위 코드를 작성하세요."
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# -----------------------------------------------------------------------------
# 4. KOBIS API 데이터 호출 함수 (1시간 동안 결과 기억/캐싱)
# 선택한 날짜(target_dt)별로 데이터를 1시간(3600초) 동안 저장하여 재요청을 방지합니다.
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office_data(key: str, target_dt: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": key,
        "targetDt": target_dt
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 throw
        return response.json(), None
    except requests.exceptions.RequestException as err:
        return None, f"네트워크 통신 오류: {err}"

# 데이터 가져오기 실행
data, network_error = fetch_box_office_data(api_key, target_date_str)

# -----------------------------------------------------------------------------
# 5. 예외 및 오류 사항 처리 (한국어 안내)
# -----------------------------------------------------------------------------
# (1) HTTP 요청 실패 또는 네트워크 오류 발생 시
if network_error:
    st.error("❌ 박스오피스 데이터를 가져오지 못했습니다.")
    st.warning(
        f"**상세 원인:** {network_error}\n\n"
        "**확인할 사항:**\n"
        "- 서버 인터넷 연결 상태를 확인해 주세요.\n"
        "- 영화진흥위원회(KOBIS) 서버가 점검 중인지 확인해 주세요."
    )
    st.stop()

# (2) API 인증키 오류 등으로 faultInfo 응답이 올 경우 (상태 코드는 200)
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ 영화진흥위원회(KOBIS) API 오류 응답이 도착했습니다.")
    st.warning(
        f"**오류 메시지:** {fault.get('message', '알 수 없는 오류')}\n"
        f"**오류 코드:** {fault.get('errorCode', 'N/A')}\n\n"
        "**확인할 사항:**\n"
        "- Streamlit Secrets의 `KOBIS_KEY` 값이 정확하게 입력되었는지 확인하세요.\n"
        "- 영화진흥위원회 오픈API 포털에서 키 일일 활용 제한량을 초과했는지 확인하세요."
    )
    st.stop()

# (3) 응답 데이터에 영화 목록이 없거나 비어 있는 경우
box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 선택하신 날짜의 박스오피스 영화 목록이 없습니다.")
    st.info("그날은 아직 집계 전입니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 6. 데이터 전처리 (문자열 -> 숫자 변환, 트로피 및 순위 화살표 가공)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# 숫자로 변환할 주요 컬럼 지정 (API 응답 문자열 -> 정수 변환)
numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 순위(rank) 기준 오름차순 정렬
df = df.sort_values("rank", ascending=True)

# [요청 기능 1] 누적관객 100만 명 이상 영화명 옆에 트로피 이모지(🏆) 추가
def format_movie_name(row):
    name = row["movieNm"]
    if row["audiAcc"] >= 1_000_000:
        return f"{name} 🏆"
    return name

df["표시영화명"] = df.apply(format_movie_name, axis=1)

# [요청 기능 2] 전날 대비 순위 증감(rankInten) 화살표 표시
# 양수: 빨간 위 화살표(🔺), 음수: 파란 아래 화살표(🔹), 0: 동일(-)
def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"

df["순위변동"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 7. 1위 영화 지표 카드(Metric) 3장 크게 보여주기
# -----------------------------------------------------------------------------
top_1 = df.iloc[0]

st.subheader(f"🥇 {display_date_str} 1위 영화")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="🎬 1위 영화명", value=top_1["표시영화명"])

with col2:
    st.metric(label="👥 해당 일자 관객수", value=f"{top_1['audiCnt']:,} 명")

with col3:
    st.metric(label="📈 누적 관객수", value=f"{top_1['audiAcc']:,} 명")

st.divider()

# -----------------------------------------------------------------------------
# 8. 관객수 상위 5편 막대그래프 시각화
# -----------------------------------------------------------------------------
st.subheader("📊 관객수 상위 5개 영화")

# 상위 5개 추출
top5_df = df.head(5).copy()

# 막대그래프 생성을 위해 영화명을 인덱스로 설정
chart_data = top5_df.set_index("표시영화명")[["audiCnt"]]
chart_data.columns = ["일일 관객수"]

st.bar_chart(chart_data)

st.divider()

# -----------------------------------------------------------------------------
# 9. 전체 박스오피스 순위 표 (순위, 순위 변동, 영화명, 개봉일, 관객수, 누적관객, 스크린수)
# -----------------------------------------------------------------------------
st.subheader("📋 일별 박스오피스 전체 순위")

# 필요한 컬럼만 추출 및 한글 컬럼명으로 변경
display_df = df[["rank", "순위변동", "표시영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "순위 변동", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

# 표 서식 및 숫자 포맷 적용
st.dataframe(
    display_df,
    column_config={
        "순위": st.column_config.NumberColumn("순위", format="%d위"),
        "관객수": st.column_config.NumberColumn("관객수", format="%d 명"),
        "누적관객": st.column_config.NumberColumn("누적관객", format="%d 명"),
        "스크린수": st.column_config.NumberColumn("스크린수", format="%d 개"),
    },
    use_container_width=True,
    hide_index=True
)
