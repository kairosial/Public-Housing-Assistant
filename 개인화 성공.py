import json
import pprint
from flask import Flask, request, jsonify
from RAG import generate_answer_with_rag
from QR import query_rewrite
from personal import *
import threading
import time
import requests

app = Flask(__name__)

public_notices = {
    "(대전충남)25년1차청년매입임대_표준입주자모집공고문": "https://online.updf.com/pdf/share?shareId=917888864738091009",
    "(정정공고문)25년1차청년매입임대_표준입주자모집공고문": "https://online.updf.com/pdf/share?shareId=917889251931070464",
    "25년 1차 청년매입임대 입주자 모집 공고문(강원지역본부)": "https://online.updf.com/pdf/share?shareId=917889416943378433",
    "25년1차청년매입임대입주자모집공고문": "https://online.updf.com/pdf/share?shareId=917889770498039809",
    "2025년 1차 대구경북 청년매입임대 입주자 모집 공고문": "https://online.updf.com/pdf/share?shareId=917889936818970625",
    "2025년1차청년매입임대입주자모집공고문(광주전남)": "https://online.updf.com/pdf/share?shareId=917890146332844032",
    "아츠스테이영등포_입주자모집공고문": "https://online.updf.com/pdf/share?shareId=917890280361828352"
}


# 사용자별 입력값 & 응답 저장
user_inputs = {}      # {'user_id': {'age': ..., 'marriage': ...}}
user_answers = {}     # {'user_id': {'age': ..., 'marriage': ..., 'final': ...}}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()

    # 🔍 전체 요청 로그
    print("\n📦 전체 JSON 요청:")
    pprint.pprint(req)

    user_input = req['userRequest']['utterance']
    user_id = req['userRequest']['user']['id']
    callback_url = req['userRequest'].get('callbackUrl')

    age = req.get("action", {}).get("clientExtra", {}).get("age")
    marriage = req.get("action", {}).get("clientExtra", {}).get("marriage")
    job = req.get("action", {}).get("clientExtra", {}).get("job")

    print(f"📥 질문 수신 from {user_id} → '{user_input}'")
    print(f"🔁 callback_url: {callback_url}")
    print(f"🔑 age: {age}, marriage: {marriage}, job : {job}")
    print("="*40)
    print(f"[📥 USER INPUT] {user_input}")
    print(f"[🧑 USER ID] {user_id}")
    print(f"[🔁 CALLBACK] {callback_url}")
    print(f"[🔐 AGE] {age} / [💍 MARRIAGE] {marriage} / [🔥 job] {job}")
    print("="*40)

    # ✅ 나이 블록 처리
    if age:
        user_inputs.setdefault(user_id, {})['age'] = age
        print(f"✅ age 저장: {user_id} → {age}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'age', age, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })

    # ✅ 결혼 블록 처리
    if marriage:
        user_inputs.setdefault(user_id, {})['marriage'] = marriage
        print(f"✅ marriage 저장: {user_id} → {marriage}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'marriage', marriage, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })
        
    if job:
        user_inputs.setdefault(user_id, {})['job'] = job
        print(f"✅ job 저장: {user_id} → {job}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'job', job, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })    

    # ✅ 결과 블록에서 최종 응답 생성 (이미 저장된 값 사용)
    user_data = user_inputs.get(user_id, {})
    age_val = user_data.get("age")
    marriage_val = user_data.get("marriage")
    job_val = user_data.get("job")
    print(f"[📦 누적 저장값] user_inputs[{user_id}] = {user_inputs.get(user_id)}")
    print(f"[✅ 최종 처리용] age_val = {age_val}, marriage_val = {marriage_val}, job_val = {job_val}")

    
    if age_val and marriage_val and job_val and user_input == '결과 확인하기':
        threading.Thread(
        target=generate_final_result_and_callback,args=(user_id, user_input, callback_url)).start()

        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })

    # ❌ age 또는 marriage 값이 없음
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                { "simpleText": { "text": "⚠️ 입력값이 부족합니다. 나이와 결혼 여부를 먼저 입력해주세요." } }
            ]
        }
    })




## 콜백

def process_answer_and_callback(user_input, callback_url, field_name, field_value, user_id):
    print(f"⏱ 백그라운드 처리 시작: {field_name} = {field_value}")
    if field_name == 'age':
        field_value = f'{field_value}살 공고 추천'
    elif field_name == 'marriage':
        field_value = f'결혼 여부 : {field_value} 공고 추천'
    elif field_name == 'job':
        field_value = f' 현재 신분 : {field_value} 공고 추천'
    
        
    answer = personal_generate_answer_with_rag(field_value,source_filter=None)
    user_answers.setdefault(user_id, {})[field_name] = answer
    print(f"✅ RAG 응답 저장: {user_id} → {field_name}: {answer}")

    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"✅ 조건에 맞는 공공주택 정보를 찾았어요!"
                    }
                }
            ],
            "quickReplies": []
        }
    }

    if field_name == "age":
        response_body["template"]["quickReplies"].append({
            "label": "결혼 정보 입력하기",
            "action": "block",
            "blockId": "67fcf8d2ee0d3d20803848f8"  # messageText 제거
        })
    elif field_name == "marriage":
        response_body["template"]["quickReplies"].append({
            "label": "직업 여부 입력하기",
            "action": "block",
            "blockId": "67fd1e80379f2578c3b83f2d"  # messageText 제거
        })
    elif field_name == "job":
        response_body["template"]["quickReplies"].append({
            "label": "결과 확인하기",
            "action": "message",
            "blockId": "67fdb6c104044e3457a1fa07"  # messageText 제거
        })

    # 디버깅용 출력 추가
    print("📤 [DEBUG] 최종 응답 JSON ↓↓↓")
    print(json.dumps(response_body, ensure_ascii=False, indent=2))

    try:
        resp = requests.post(callback_url, headers={"Content-Type": "application/json"}, json=response_body)
        print(f"📤 Callback 전송 완료 → {field_name}, 상태 코드: {resp.status_code}")
        print("📥 카카오 응답 내용:", resp.text)
    except Exception as e:
        print(f"❌ Callback 실패: {e}")

## 최종 응답 콜백

def generate_final_result_and_callback(user_id, user_input, callback_url):
    age_val = user_inputs.get(user_id, {}).get("age")
    marriage_val = user_inputs.get(user_id, {}).get("marriage")
    job_val = user_inputs.get(user_id, {}).get("job")

    if not (age_val and marriage_val and job_val):
        return

    print(f"🧠 최종 응답 생성 시작: age={age_val}, marriage={marriage_val}")
    condition = f'나이 : {age_val}, 결혼여부 : {marriage_val}, 직업 : {job_val}'

    final = (
        user_answers[user_id].get('age', '') + '\n' +
        user_answers[user_id].get('marriage', '') + '\n' +
        user_answers[user_id].get('job', '')
    )
    final_result = final_gpt(final, condition)
    user_answers.setdefault(user_id, {})['final'] = final_result

    response_body = {
    "version": "2.0",
    "template": {
        "outputs": [
            { "simpleText": { "text": final_result } }
        ],
        "quickReplies": [
            {
                "label": "정보 다시 입력하기",
                "action": "block",
                "blockId": "67fcf6b9379f2578c3b838b6"  # 오픈빌더에서 다시 입력 받을 시작 블록 ID로 변경
            },
            {
                "label": "메뉴로 돌아가기",
                "action": "block",
                "blockId": "67fb9b2c202e764481ad480e"  # 오픈빌더에서 메인 메뉴로 가는 블록 ID로 변경
            }
        ]
    }
}


    try:
        print("📤 [DEBUG] 최종 결과 콜백 전송 ↓↓↓")
        print(json.dumps(response_body, ensure_ascii=False, indent=2))

        resp = requests.post(callback_url, headers={"Content-Type": "application/json"}, json=response_body)
        print(f"📤 Callback 전송 완료 → 결과 확인, 상태 코드: {resp.status_code}")
        print("📥 카카오 응답 내용:", resp.text)

    except Exception as e:
        print(f"❌ Callback 실패: {e}")



if __name__ == "__main__":
    print("✅ Flask 서버 실행 중 (port 5000)...")
    app.run(host="0.0.0.0", port=5000)
