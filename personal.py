from dotenv import load_dotenv
from QR import query_rewrite
import os
import requests
import re
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

# .env 로딩
load_dotenv()

# 환경변수
embedding_api_key = os.getenv('Embedding_API_KEY')
embedding_endpoint = os.getenv('Embedding_ENDPOINT')
embedding_api_version = os.getenv('embedding_api_version')
embedding_deployment = os.getenv('embedding_deployment')
ai_search_endpoint = os.getenv("add_new_index_Search_ENDPOINT")
ai_search_api_key = os.getenv('AI_Search_API_KEY')
#llm_endpoint = os.getenv('OPENAI_ENDPOINT')
#llm_api_key = os.getenv('OPENAI_API_KEY')
llm_endpoint = os.getenv('OPENAI_ENDPOINT_2')
llm_api_key = os.getenv('OPENAI_API_KEY_2')

# 임베딩 객체
embedding = AzureOpenAIEmbeddings(
    api_key = embedding_api_key,
    azure_endpoint = embedding_endpoint,
    model = embedding_deployment,
    openai_api_version = embedding_api_version
)

# 벡터 검색
def personal_request_ai_search(query: str, source_filter: str = None, k: int = 10) -> list:
    headers = {
        "Content-Type": "application/json",
        "api-key": ai_search_api_key
    }

    query_vector = embedding.embed_query(query)

    body = {
        "search": query,
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": query_vector,
                "fields": "embedding",
                "k": k
            }
        ]
    }

    if source_filter:
        cleaned_source = source_filter.replace(".pdf", "")
        body["filter"] = f"source eq '{cleaned_source}'"

    response = requests.post(ai_search_endpoint, headers=headers, json=body)

    if response.status_code != 200:
        print(f"❌ 검색 실패: {response.status_code}")
        print(response.text)
        return []

    return [
        {
            "content": item["content"],
            "source": item.get("source", ""),
            "score": item.get("@search.score", 0)
        }
        for item in response.json()["value"]
    ]

# GPT 응답 요청
def personal_request_gpt(prompt: str) -> str:
    headers = {
        'Content-Type': 'application/json',
        'api-key': llm_api_key
    }

    body = {
        "messages": [
            {"role": "system", "content": "너는 친절하고 정확한 AI 도우미야. 사용자 질문에 문서 기반으로 답해줘."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(llm_endpoint, headers=headers, json=body)
    if response.status_code == 200:
        
        content = response.json()['choices'][0]['message']['content']
        return re.sub(r'\[doc(\d+)\]', r'[참조 \1]', content)
    else:
        print("❌ GPT 요청 실패:", response.status_code, response.text)
        return "⚠️ 오류가 발생했습니다."

# 최종 RAG 응답 생성 함수
def personal_generate_answer_with_rag(query: str, source_filter: str = None, top_k: int = 3) -> str:
    results = personal_request_ai_search(query, source_filter=source_filter, k=top_k)
    if not results:
        return "❌ 관련 문서를 찾을 수 없습니다."

    #context = "\n\n".join([f"[doc{i+1}]\n{item['content']}" for i, item in enumerate(results)])
    context = "\n\n".join([f"[{item['source']}]\n{item['content']}" for item in results])
    prompt = f"""아래 문서를 참고해서 어떤 공고문을 사용자의 질문에 맞게 추천해줄 수 있는지 1위부터 3위까지 순위를 매겨줘.
                이후 순위를 왜 그렇게 설정했는지 각각 이유도 자세하게 설명해줘.
                답변은 500자 이내로 작성해줘.
[사용자 질문]
{query}

[참고 문서]
{context}

답변:"""
    return personal_request_gpt(prompt)


# 최종 공고문 선택
def final_gpt(prompt,final_result):
    headers = {
        'Content-Type': 'application/json',
        'api-key': llm_api_key
    }

    body = {
        "messages": [
            {"role": "system", "content": """너는 친절하고 정확한 AI 도우미야. 아래 조건별로 이미 추천된 공고문 순위들을 종합해 최종 1~3위를 매기고, 각 공고에 대해 종합적으로 평가해서 점수(10점 만점)를 매기고 이유를 상세히 설명해줘.  
                응답 형식은 다음과 같아야 해:

                최종 종합 순위와 이유는 다음과 같습니다:

                &
                1위: [공고문 이름]**
                이유 설명

                &
                2위: [공고문 이름]**
                이유 설명

                &
                3위: [공고문 이름]**
                이유 설명

                중간에 다른 텍스트는 넣지 말고 정확히 이 포맷을 지켜줘."""},

            {"role": "user", "content": f"조건 : {final_result}, 조건별 순위 : {prompt}"}
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(llm_endpoint, headers=headers, json=body)
    if response.status_code == 200:
        
        content = response.json()['choices'][0]['message']['content']
        return re.sub(r'\[doc(\d+)\]', r'[참조 \1]', content)
    else:
        print("❌ GPT 요청 실패:", response.status_code, response.text)
        return "⚠️ 오류가 발생했습니다."

# field_value = f'19~39살 공고 추천'
# # answer = personal_request_ai_search(field_value, source_filter=None)
# # print(answer)
# result = personal_generate_answer_with_rag(field_value,source_filter=None)
# print(result)