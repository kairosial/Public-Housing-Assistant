from flask import Flask, request, jsonify
from RAG import generate_answer_with_rag, generate_answer_with_llm
from QR import query_rewrite, yoyak
import threading
import time
import json
import requests

app = Flask(__name__)

# 사용자별 source_filter 저장
user_file_choices = {}

# 사용자별 최근 answer 저장
user_answers = {}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()
    user_input = req['userRequest']['utterance']
    user_id = req['userRequest']['user']['id']
    callback_url = req['userRequest'].get('callbackUrl')
    source_filter = req.get("action", {}).get("clientExtra", {}).get("source_filter")

    print("\n📥 질문 수신:", user_input)
    print("🔁 callback_url:", callback_url)
    print("🔑 source_filter:", source_filter)

    # ✅ 1) 선택완료 블록에서 들어온 요청: source_filter 저장만
    if source_filter:
        user_file_choices[user_id] = source_filter
        print(f"✅ source_filter 저장됨: {user_id} → {source_filter}")
        return jsonify({ "status": "ok" })  # 카카오에서 봇 응답 따로 지정했으니 최소 응답만

    # ✅ 2) '요약하기' 요청인 경우
    if user_input.strip() == "요약하기":
        prev_answer = user_answers.get(user_id)
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
        user_answers[user_id] = answer

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

def process_request(user_input, callback_url, source_filter, user_id):
    print("⏱ 백그라운드에서 LLM 처리 시작")
    start = time.time()

    if source_filter:
        answer = generate_answer_with_rag(user_input, source_filter)
    else:
        answer = generate_answer_with_llm(user_input)
    
    user_answers[user_id] = answer
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
