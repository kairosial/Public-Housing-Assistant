from flask import Flask, request, jsonify
from RAG import generate_answer_with_rag
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

    print("📥 질문 수신:", user_input)
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
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {"text": "❗먼저 '도움말'에서 파일을 선택해주세요."}
                }]
            }
        })

    user_input = query_rewrite(user_input)

    if callback_url:
        threading.Thread(target=process_request, args=(user_input, callback_url, chosen_file, user_id)).start()
        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })
    else:
        answer = generate_answer_with_rag(user_input, source_filter=chosen_file)
        user_answers[user_id] = answer
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{ "simpleText": { "text": answer } }],
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

    answer = generate_answer_with_rag(user_input, source_filter)
    user_answers[user_id] = answer
    elapsed = time.time() - start
    print(f"✅ 응답 완료 (처리 시간: {elapsed:.2f}초)")

    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [{ "simpleText": { "text": answer } }],
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
