# 매칭 함수 (담당: 김란)
# 1) 제외 조건 판정  2) 일치율 계산  3) 매물에서 출발하는 상위 5명 추천
# 계산식은 중간보고서 2.3.2 ~ 2.3.5를 따른다.

ITEMS = ["time", "clean", "noise", "social"]          # 생활 시간대, 청결, 소음, 교류
ITEM_NAMES = {"time": "생활 시간대", "clean": "청결", "noise": "소음", "social": "교류"}
MIN_RATE = 60       # 이 점수 미만은 추천하지 않음
TOP_N = 5           # 최대 추천 인원


# ---------- 작은 도우미 ----------

def in_range(value, low, high):
    """value가 low 이상 high 이하이면 True."""
    return low <= value and value <= high


def month_number(text):
    """'2027-03' 같은 연-월 글자를 비교하기 쉬운 숫자로 바꾼다. (연 × 12 + 월)"""
    year = int(text[0:4])
    month = int(text[5:7])
    return year * 12 + month


def fits_property(user, prop):
    """한 사람이 그 매물에 맞는지 본다. -> 맞으면 None, 안 맞으면 사유 글자.
    1인 부담액 = 매물 금액 ÷ 2"""
    if prop["dong"] not in user["areas"]:
        return "희망 지역"
    deposit_each = prop["deposit"] / 2
    rent_each = prop["rent"] / 2
    if not in_range(deposit_each, user["deposit_min"], user["deposit_max"]):
        return "예산"
    if not in_range(rent_each, user["rent_min"], user["rent_max"]):
        return "예산"
    return None


# ---------- 1) 제외 조건 판정 ----------

def is_excluded(a, b, prop=None):
    """두 사람이 함께 살 수 없는 조건이 하나라도 있으면 (True, 사유), 없으면 (False, "").
    prop(매물)이 주어지면 희망 지역과 예산도 그 매물 기준으로 판정한다.
    (매물 없이 룸메이트부터 찾는 경로의 지역·예산 판정은 별도 함수로 추가 예정)"""
    # 1. 성별: 서로가 희망하는 상대 성별과 맞아야 함
    if a["want_gender"] != b["gender"] or b["want_gender"] != a["gender"]:
        return True, "성별"

    # 2. 흡연: 상대가 흡연자인데 내가 허용하지 않으면 제외 (양쪽 모두 확인)
    if (b["smoke"] and not a["smoke_ok"]) or (a["smoke"] and not b["smoke_ok"]):
        return True, "흡연"

    # 3. 반려동물: 상대가 키우는데 내가 허용하지 않으면 제외 (양쪽 모두 확인)
    if (b["pet"] and not a["pet_ok"]) or (a["pet"] and not b["pet_ok"]):
        return True, "반려동물"

    # 4·5. 희망 지역, 예산: 매물이 있을 때만 판정
    if prop is not None:
        reason = fits_property(a, prop)
        if reason is None:
            reason = fits_property(b, prop)
        if reason is not None:
            return True, reason

    # 6. 거주 기간: 12개월 넘게 차이 나면 제외
    if abs(a["months"] - b["months"]) > 12:
        return True, "거주 기간"

    # 7. 입주 시기: 1개월 넘게 차이 나면 제외
    if abs(month_number(a["move_in"]) - month_number(b["move_in"])) > 1:
        return True, "입주 시기"

    return False, ""


# ---------- 2) 일치율 계산 ----------

def calc_importance(user, item):
    """항목의 중요도. 청결·소음은 6 - 값, 생활 시간대·교류는 1 + 2 × |값 - 3|"""
    value = user[item]
    if item == "clean" or item == "noise":
        return 6 - value
    return 1 + 2 * abs(value - 3)


def calc_match_rate(a, b):
    """두 사람의 일치율을 계산한다.
    -> (일치율 0~100 소수 첫째 자리, 항목별 유사도 딕셔너리, A 입장 점수, B 입장 점수)"""
    similarity = {}
    sum_wa = 0
    sum_wb = 0
    score_a = 0
    score_b = 0
    for item in ITEMS:
        s = 1 - abs(a[item] - b[item]) / 4
        wa = calc_importance(a, item)
        wb = calc_importance(b, item)
        similarity[item] = s
        score_a = score_a + wa * s
        score_b = score_b + wb * s
        sum_wa = sum_wa + wa
        sum_wb = sum_wb + wb

    s_ab = score_a / sum_wa
    s_ba = score_b / sum_wb
    rate = 100 * (s_ab * s_ba) ** 0.5
    return round(rate, 1), similarity, s_ab, s_ba


# ---------- 3) 매물에서 출발하는 추천 ----------

def recommend_for_property(me, prop, users, interested_ids, skip_ids=None):
    """매물을 고른 사용자에게 같은 매물에 관심을 등록한 사람 중 잘 맞는 상위 5명을 추천한다.

    me             : 나 (사용자 딕셔너리)
    prop           : 고른 매물 (매물 딕셔너리)
    users          : 전체 사용자 리스트
    interested_ids : 이 매물에 관심을 등록한 사용자 ID 리스트
    skip_ids       : 추천에서 뺄 사용자 ID 리스트 (예: 이 매물에서 이미 거절한 사람)

    -> 딕셔너리 {
         "my_reason": 내가 이 매물에 맞지 않으면 사유, 맞으면 None,
         "results":   [{"user":..., "rate":..., "similarity":...}, ...] 높은 순 최대 5개,
         "excluded":  {사유: 제외된 인원, ...}  (추천이 없을 때 안내용)
       }"""
    if skip_ids is None:
        skip_ids = []

    result = {"my_reason": None, "results": [], "excluded": {}}

    # 1단계: 나부터 이 매물에 맞는지 확인
    my_reason = fits_property(me, prop)
    if my_reason is not None:
        result["my_reason"] = my_reason
        return result

    # 2단계: 후보마다 제외 조건 판정과 일치율 계산
    passed = []
    for other in users:
        if other["user_id"] == me["user_id"]:
            continue
        if other["user_id"] not in interested_ids:
            continue
        if other["user_id"] in skip_ids:
            continue

        excluded, reason = is_excluded(me, other, prop)
        if excluded:
            result["excluded"][reason] = result["excluded"].get(reason, 0) + 1
            continue

        rate, similarity, s_me, s_other = calc_match_rate(me, other)
        if rate < MIN_RATE:
            result["excluded"]["일치율 60점 미만"] = result["excluded"].get("일치율 60점 미만", 0) + 1
            continue

        passed.append({"user": other, "rate": rate, "similarity": similarity,
                       "low_score": min(s_me, s_other),
                       "month_gap": abs(me["months"] - other["months"])})

    # 3단계: 정렬 (일치율 높은 순 → 두 입장 중 낮은 점수가 높은 순 → 거주 기간 차이 작은 순 → ID 순)
    passed.sort(key=lambda c: (-c["rate"], -c["low_score"], c["month_gap"], c["user"]["user_id"]))

    result["results"] = passed[:TOP_N]
    return result
