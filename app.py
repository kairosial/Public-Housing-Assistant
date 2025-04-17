from flask import Flask, request, jsonify
from RAG2 import generate_answer_with_rag, generate_answer_with_llm
from QR import query_rewrite, yoyak
from personal import *
import threading
import time
import json
import requests

app = Flask(__name__)

# 사용자별 source_filter 저장
user_file_choices = {}
user_inputs = {}
# 사용자별 최근 answer 저장
user_answers = {}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()
    user_input = req['userRequest']['utterance']
    user_id = req['userRequest']['user']['id']
    callback_url = req['userRequest'].get('callbackUrl')
    source_filter = req.get("action", {}).get("clientExtra", {}).get("source_filter")
    
    age = req.get("action", {}).get("clientExtra", {}).get("age")
    marriage = req.get("action", {}).get("clientExtra", {}).get("marriage")
    job = req.get("action", {}).get("clientExtra", {}).get("job")
    
    print("\n📥 질문 수신:", user_input)
    print("🔁 callback_url:", callback_url)
    print("🔑 source_filter:", source_filter)


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
    
    # ✅ 1) 선택완료 블록에서 들어온 요청: source_filter 저장만
    if source_filter:
        user_file_choices[user_id] = source_filter
        print(f"✅ source_filter 저장됨: {user_id} → {source_filter}")
        return jsonify({ "status": "ok" })  # 카카오에서 봇 응답 따로 지정했으니 최소 응답만

    # ✅ 2) '요약하기' 요청인 경우
    if user_input.strip() == "요약하기":
        prev_answer = user_answers.get(user_id, {}).get("general")
        if not prev_answer:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "⚠️ 요약할 응답이 없습니다. 먼저 질문을 해주세요."}}]
                }
            })
        
        summarized = yoyak(prev_answer)
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": summarized}}]
            }
        })

    # ✅ 3) 일반 질문 처리 (폴백 블록)
    chosen_file = user_file_choices.get(user_id)
    if not chosen_file:
        print("⚠️ 선택된 파일 없음 → 전체 데이터 또는 기본 응답으로 처리합니다.")
        chosen_file = None  # 전체 소스로 RAG 처리하거나 기본 설정으로

    user_input = query_rewrite(user_input)

    if callback_url:
        threading.Thread(target=process_request, args=(user_input, callback_url, chosen_file, user_id)).start()
        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })
    else:
        if chosen_file:
            answer = generate_answer_with_rag(user_input, source_filter=chosen_file)
        else:
            answer = generate_answer_with_llm(user_input)
        if not isinstance(user_answers.get(user_id), dict):
            user_answers[user_id] = {}
        user_answers[user_id]["general"] = answer

        # 여기서 answer가 JSON 문자열(구조화된 답변)라고 가정
        try:
            answer_json = json.loads(answer)
            sections = answer_json.get("sections", [])
        except json.JSONDecodeError:
            # JSON 파싱 실패시 fallback: 전체 답변을 하나의 섹션으로 처리
            sections = [{"title": "답변", "content": answer}]

        # 각 섹션을 BasicCard 형식 아이템으로 변환
        items = []
        for sec in sections:
            items.append({
                "title": sec.get("title", ""),
                "description": sec.get("content", "")
            })

        # 최종 카카오톡 Carousel 응답 JSON 구성
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "carousel": {
                            "type": "basicCard",
                            "items": items
                        }
                    }
                ],
                "quickReplies": [
                    {
                        "label": "요약하기",
                        "action": "message",
                        "messageText": "요약하기"
                    }
                ]
            }
        })
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


def process_request(user_input, callback_url, source_filter, user_id):
    print("⏱ 백그라운드에서 LLM 처리 시작")
    start = time.time()

    if source_filter:
        answer = generate_answer_with_rag(user_input, source_filter)
    else:
        answer = generate_answer_with_llm(user_input)
    
    if not isinstance(user_answers.get(user_id), dict):
        user_answers[user_id] = {}
    user_answers[user_id]["general"] = answer
    
    elapsed = time.time() - start
    print(f"✅ 응답 완료 (처리 시간: {elapsed:.2f}초)")

    try:
        answer_json = json.loads(answer)
        sections = answer_json.get("sections", [])
    except json.JSONDecodeError:
        sections = [{"title": "답변", "content": answer}]
    
    items = []
    for sec in sections:
        items.append({
            "title": sec.get("title", ""),
            "description": sec.get("content", "")
        })
    
    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": items
                    }
                }
            ],
            "quickReplies": [
                {
                    "label": "요약하기",
                    "action": "message",
                    "messageText": "요약하기"
                }
            ]
        }
    }
    
    headers = { "Content-Type": "application/json" }
    try:
        resp = requests.post(callback_url, headers=headers, json=response_body)
        print("📤 Callback 응답 전송, 상태 코드:", resp.status_code)
    except Exception as e:
        print("❌ Callback 전송 실패:", e)

if __name__ == "__main__":
    print("✅ Flask 서버 실행 중 (port 5000)...")
    app.run(port=5000)