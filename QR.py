from dotenv import load_dotenv
import requests
import re
import os

load_dotenv("E:/work/MS_project_2/code/.env")
# 사용자 프롬프트
# Azure OpenAI API의 엔드포인트 URL
OPENAI_ENDPOINT = os.getenv('OPENAI_ENDPOINT_2')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_2')
#OPENAI_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
#OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Azure OpenAI API 키
def query_rewrite(user_query):
    headers = {
        'Content-Type': 'application/json',
        'api-key': OPENAI_API_KEY
    }
    prompt = f"""
    다음 사용자의 질문을 검색에 적합한 간결한 키워드 형태의 질의로 바꿔줘.
    사용자의 질문: "{user_query}"
    검색용 질의:
    """
    
    body = {
        "messages": [
            {"role": "system", "content": """너는 질문을 키워드 형태로 변환하는 query rewrite 봇이야
             예시
             사용자의 질문 : 그래서 뭘 내야돼?
             검색용 질의 : 필요 제출 서류
             """},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }
    
    response = requests.post(OPENAI_ENDPOINT, headers=headers, json=body)
    if response.status_code == 200:
        response_json = response.json()
        result = response_json["choices"][0]["message"]["content"].strip()
        return result
    else:
        print("❌ GPT 요청 실패:", response.status_code, response.text)
        return "⚠️ 오류가 발생했습니다."

def yoyak(user_query):
    headers = {
        'Content-Type': 'application/json',
        'api-key': OPENAI_API_KEY
    }
    prompt = f"""
    다음 사용자의 질문을 요약해줘.
    사용자의 질문: "{user_query}"
    요약본:
    """
    
    body = {
        "messages": [
            {"role": "system", "content": """
            너는 사용자가 이해하기 쉽도록 정보를 요약해주는 AI 비서야. 아래 내용을 핵심만 간결하게 요약해줘.
            - 꼭 필요한 정보만 뽑아서 5줄 이내로 정리해.
            - 문단이 아닌 **목록 스타일**로 보여줘.
            - 한 문장당 1줄 이내, 최대한 짧고 직관적으로!
            - 📌, ✅, ✨ 등 이모지와 굵은 글씨(**bold**)를 활용해서 가독성 높여줘.
            - 카카오톡 메시지처럼 가볍고 쉽게 전달해.
            - *는 쓰지마
[요약할 내용]
{text}

             """},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }
    
    response = requests.post(OPENAI_ENDPOINT, headers=headers, json=body)
    if response.status_code == 200:
        response_json = response.json()
        result = response_json["choices"][0]["message"]["content"].strip()
        return result
    else:
        print("❌ GPT 요청 실패:", response.status_code, response.text)
        return "⚠️ 오류가 발생했습니다."

print(OPENAI_ENDPOINT)
print(OPENAI_API_KEY)

