# 데이터 읽기·저장 함수 (담당: 김민서)
# data 폴더의 CSV 파일을 읽어 딕셔너리 리스트로 바꾸고, 새 데이터를 저장한다.

import csv
import os
from datetime import datetime

# data 폴더 위치 (이 파일이 src 안에 있으므로 한 단계 위의 data 폴더)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

USERS_FILE = os.path.join(DATA_DIR, "users.csv")
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.csv")
INTERESTS_FILE = os.path.join(DATA_DIR, "interests.csv")
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.csv")

USER_FIELDS = ["user_id", "nickname", "gender", "want_gender", "areas",
               "deposit_min", "deposit_max", "rent_min", "rent_max",
               "months", "move_in", "smoke", "smoke_ok", "pet", "pet_ok",
               "time", "clean", "noise", "social", "chat_link"]
INTEREST_FIELDS = ["user_id", "property_id", "created_at"]
REQUEST_FIELDS = ["request_id", "from_id", "to_id", "property_id",
                  "match_rate", "status", "created_at", "updated_at"]

NUMBER_FIELDS = ["deposit_min", "deposit_max", "rent_min", "rent_max",
                 "months", "time", "clean", "noise", "social"]
YN_FIELDS = ["smoke", "smoke_ok", "pet", "pet_ok"]


# ---------- 공통 도우미 ----------

def now_text():
    """현재 시각을 '2026-11-02 14:30' 형식의 글자로 돌려준다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def read_rows(path):
    """CSV 파일을 읽어 행(딕셔너리)의 리스트로 돌려준다. 파일이 없으면 빈 리스트."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, fields, rows):
    """행 리스트 전체를 CSV 파일에 새로 쓴다."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------- 사용자 ----------

def row_to_user(row):
    """CSV 한 줄(모두 글자)을 계산에 쓸 수 있는 형태로 바꾼다."""
    user = dict(row)
    user["areas"] = row["areas"].split(";")          # "명륜1가;혜화동" -> ["명륜1가", "혜화동"]
    for key in NUMBER_FIELDS:
        user[key] = int(row[key])                    # "500" -> 500
    for key in YN_FIELDS:
        user[key] = (row[key] == "Y")                # "Y" -> True, "N" -> False
    return user


def user_to_row(user):
    """사용자 딕셔너리를 CSV에 쓸 수 있는 글자 형태로 바꾼다."""
    row = {}
    for key in USER_FIELDS:
        value = user.get(key, "")
        if key == "areas":
            value = ";".join(value)
        elif key in YN_FIELDS:
            if value:
                value = "Y"
            else:
                value = "N"
        row[key] = value
    return row


def load_users():
    """모든 사용자를 불러온다. -> 사용자 딕셔너리의 리스트"""
    users = []
    for row in read_rows(USERS_FILE):
        users.append(row_to_user(row))
    return users


def find_user(users, user_id):
    """사용자 리스트에서 ID가 같은 사용자를 찾는다. 없으면 None."""
    for user in users:
        if user["user_id"] == user_id:
            return user
    return None


def new_user_id(users):
    """새 사용자 ID를 만든다. (가장 큰 번호 + 1, 예: u021)"""
    biggest = 0
    for user in users:
        number = int(user["user_id"][1:])
        if number > biggest:
            biggest = number
    return "u" + str(biggest + 1).zfill(3)


def save_user(user):
    """사용자를 저장한다. ID가 없으면 새로 추가하고, 있으면 내용을 바꾼다. -> 저장된 user_id"""
    users = load_users()
    if user.get("user_id", "") == "":
        user["user_id"] = new_user_id(users)
        users.append(user)
    else:
        found = False
        for i in range(len(users)):
            if users[i]["user_id"] == user["user_id"]:
                users[i] = user
                found = True
        if not found:
            users.append(user)

    rows = []
    for one in users:
        rows.append(user_to_row(one))
    write_rows(USERS_FILE, USER_FIELDS, rows)
    return user["user_id"]


# ---------- 매물 ----------

def load_properties():
    """모든 매물을 불러온다. -> 매물 딕셔너리의 리스트 (보증금·월세는 숫자)"""
    properties = []
    for row in read_rows(PROPERTIES_FILE):
        prop = dict(row)
        prop["deposit"] = int(row["deposit"])
        prop["rent"] = int(row["rent"])
        properties.append(prop)
    return properties


def find_property(properties, property_id):
    """매물 리스트에서 ID가 같은 매물을 찾는다. 없으면 None."""
    for prop in properties:
        if prop["property_id"] == property_id:
            return prop
    return None


# ---------- 관심 등록 ----------

def load_interests():
    """모든 관심 등록 기록을 불러온다. -> [{"user_id":..., "property_id":..., "created_at":...}, ...]"""
    return read_rows(INTERESTS_FILE)


def add_interest(user_id, property_id):
    """매물에 관심을 등록한다. 이미 등록했으면 다시 저장하지 않는다. -> True(새로 등록) / False(이미 있음)"""
    interests = load_interests()
    for item in interests:
        if item["user_id"] == user_id and item["property_id"] == property_id:
            return False
    interests.append({"user_id": user_id, "property_id": property_id, "created_at": now_text()})
    write_rows(INTERESTS_FILE, INTEREST_FIELDS, interests)
    return True


def remove_interest(user_id, property_id):
    """관심 등록을 취소한다."""
    interests = load_interests()
    remain = []
    for item in interests:
        if not (item["user_id"] == user_id and item["property_id"] == property_id):
            remain.append(item)
    write_rows(INTERESTS_FILE, INTEREST_FIELDS, remain)


def get_interested_user_ids(property_id):
    """그 매물에 관심을 등록한 사용자 ID 리스트를 돌려준다."""
    ids = []
    for item in load_interests():
        if item["property_id"] == property_id:
            ids.append(item["user_id"])
    return ids


# ---------- 매칭 요청 ----------

def load_requests():
    """모든 매칭 요청을 불러온다. (match_rate는 숫자로 바꿈)"""
    requests = read_rows(REQUESTS_FILE)
    for req in requests:
        req["match_rate"] = float(req["match_rate"])
    return requests


def new_request_id(requests):
    """새 요청 번호를 만든다. (예: M001)"""
    biggest = 0
    for req in requests:
        number = int(req["request_id"][1:])
        if number > biggest:
            biggest = number
    return "M" + str(biggest + 1).zfill(3)


def add_request(from_id, to_id, property_id, match_rate):
    """매칭 요청을 저장한다. 매물 없이 보낸 요청은 property_id를 ""로 둔다.
    같은 두 사람·같은 매물로 '대기' 중인 요청이 있으면 저장하지 않고 None을 돌려준다.
    -> 새 요청 번호 또는 None"""
    requests = load_requests()
    for req in requests:
        if (req["from_id"] == from_id and req["to_id"] == to_id
                and req["property_id"] == property_id and req["status"] == "대기"):
            return None
    request_id = new_request_id(requests)
    requests.append({"request_id": request_id, "from_id": from_id, "to_id": to_id,
                     "property_id": property_id, "match_rate": match_rate,
                     "status": "대기", "created_at": now_text(), "updated_at": now_text()})
    write_rows(REQUESTS_FILE, REQUEST_FIELDS, requests)
    return request_id


def update_request_status(request_id, status):
    """요청 상태를 바꾼다. status는 "수락", "거절", "만료" 중 하나. -> True(성공) / False(번호 없음)"""
    requests = load_requests()
    changed = False
    for req in requests:
        if req["request_id"] == request_id:
            req["status"] = status
            req["updated_at"] = now_text()
            changed = True
    if changed:
        write_rows(REQUESTS_FILE, REQUEST_FIELDS, requests)
    return changed


def get_requests_for(user_id):
    """한 사용자의 받은 요청과 보낸 요청을 나눠 돌려준다. -> (받은 요청 리스트, 보낸 요청 리스트)"""
    received = []
    sent = []
    for req in load_requests():
        if req["to_id"] == user_id:
            received.append(req)
        if req["from_id"] == user_id:
            sent.append(req)
    return received, sent
