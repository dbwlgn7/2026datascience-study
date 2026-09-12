import re
import pandas as pd
import requests

# ---------------------------------------------------------
# 1. 학교 코드 조회 함수 (schoolInfo)
# ---------------------------------------------------------
def get_school_code(school_name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": school_name}

    response = requests.get(url, params=params)
    data = response.json()

    if "schoolInfo" in data:
        row = data["schoolInfo"][1]["row"][0]
        return {
            "school_name": row["SCHUL_NM"],
            "ofcdc_code": row["ATPT_OFCDC_SC_CODE"],
            "school_code": row["SD_SCHUL_CODE"],
        }
    else:
        print(f"[{school_name}] 학교 정보를 찾을 수 없습니다.")
        return None


# ---------------------------------------------------------
# 2. 급식 식단 조회 함수 (mealServiceDietInfo)
# ---------------------------------------------------------
def get_meal_data(ofcdc_code, school_code, from_ymd, to_ymd, api_key=None):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ofcdc_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
        "pSize": 100,  # 인증키 등록 시 최대 1000까지 가능
    }
    if api_key:
        params["KEY"] = api_key

    response = requests.get(url, params=params)
    data = response.json()

    if "mealServiceDietInfo" in data:
        return data["mealServiceDietInfo"][1]["row"]
    else:
        return []


# ---------------------------------------------------------
# 3. 메뉴 텍스트 정제 및 잔반 위험도 가중치 계산 함수
# ---------------------------------------------------------
def clean_and_score_meal(ddish_nm):
    # <br/> 태그 분리 및 알레르기 번호(숫자.숫자...) 제거
    raw_dishes = ddish_nm.split("<br/>")
    cleaned_dishes = []
    
    for dish in raw_dishes:
        # 괄호와 안의 알레르기 번호 제거 (예: 돈가스 (1.2.5.6) -> 돈가스)
        clean_dish = re.sub(r"\([0-9\.]+\)", "", dish).strip()
        if clean_dish:
            cleaned_dishes.append(clean_dish)

    # 비선호/선호 조리법 기반 잔반 위험도 가중치 부여 (예시 규칙)
    high_waste_keywords = ["무침", "나물", "청국장", "조림", "시래기", "숙채"]
    low_waste_keywords = ["돈가스", "치킨", "스파게티", "마라", "불고기", "튀김"]

    risk_score = 1.0  # 기본 점수 (1~5점 스케일)

    for dish in cleaned_dishes:
        for kw in high_waste_keywords:
            if kw in dish:
                risk_score += 0.8
        for kw in low_waste_keywords:
            if kw in dish:
                risk_score -= 0.5

    # 1.0 ~ 5.0 사이로 점수 정규화
    final_risk_score = round(max(1.0, min(5.0, risk_score)), 1)

    return cleaned_dishes, final_risk_score


# ---------------------------------------------------------
# 4. 메인 실행: 3개 학교 데이터 병합 및 데이터프레임 생성
# ---------------------------------------------------------
target_schools = ["인천남동고등학교", "인천고등학교", "석정여고"]
start_date = "20260901"
end_date = "20260930"

all_meal_records = []

for school_nm in target_schools:
    info = get_school_code(school_nm)
    if info:
        meals = get_meal_data(
            info["ofcdc_code"], info["school_code"], start_date, end_date
        )

        for m in meals:
            dishes, risk_score = clean_and_score_meal(m["DDISH_NM"])

            # 칼로리 숫자만 추출 (예: "1300.4 Kcal" -> 1300.4)
            cal_match = re.search(r"[\d\.]+", m.get("CAL_INFO", "0"))
            calories = float(cal_match.group()) if cal_match else 0.0

            all_meal_records.append({
                "학교명": info["school_name"],
                "급식일": m["MLSV_YMD"],
                "메뉴목록": dishes,
                "메뉴수": len(dishes),
                "잔반위험도": risk_score,
                "칼로리(kcal)": calories,
                "원본메뉴": m["DDISH_NM"],
            })

# Streamlit 대시보드에서 바로 쓸 수 있는 Pandas DataFrame으로 변환
df_meals = pd.DataFrame(all_meal_records)
print(df_meals.head())
