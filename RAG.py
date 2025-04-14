from dotenv import load_dotenv
from QR import query_rewrite
import os
import requests
import re
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

# .env 로딩
load_dotenv("E:/work/MS_project_2/code/.env")

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
def request_ai_search(query: str, source_filter: str = None, k: int = 5) -> list:
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
def request_gpt(prompt: str) -> str:
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
def generate_answer_with_rag(query: str, source_filter: str = None, top_k: int = 3) -> str:
    results = request_ai_search(query, source_filter=source_filter, k=top_k)
    if not results:
        return "❌ 관련 문서를 찾을 수 없습니다."

    #context = "\n\n".join([f"[doc{i+1}]\n{item['content']}" for i, item in enumerate(results)])
    context = "\n\n".join([f"[{item['source']}]\n{item['content']}" for item in results])
    prompt = f"""사용자의 질문에 대해 아래 문서를 참고해서 간단하고 핵심적인 답변을 만들어줘.
                또한 답변에 어떤 문서에서 나온 정보인지 간단히 출처를 괄호로 남겨줘.
                출처는 문장 맨 위에 남기고 \n 한 뒤에 답변
                답변은 1000자 이내로 작성해줘.
[사용자 질문]
{query}

[참고 문서]
{context}

답변:"""
    return request_gpt(prompt)

#prompt = '나 경기도 사는 멋쟁이 윤홍원... 나이는 26살이고 대학은 졸업했으나 무직이야 근데 내집마련을 하고싶은데 추천할만한 공고문 있어?'
prompt = '''경기도 거주,나이는 26세, 대학 졸업, 무직
            제출해야할 서류'''
new_prompt = query_rewrite(prompt)
print('🐶new_prompt',new_prompt)
chunk_result = request_ai_search(new_prompt,source_filter=None)
result = generate_answer_with_rag(new_prompt,source_filter=None)

i = 1
for chunk in chunk_result:
    print('============================')
    print(f'🤖 top {i} result : {chunk}')
    i += 1
    if i == 10:
        break
    
print('============================')
print('============================')
print(f'🤖chunk_result🤖 = {result}')
print('hi')