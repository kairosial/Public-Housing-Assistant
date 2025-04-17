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
ai_search_endpoint = os.getenv("pdf_vocab_gh_fixed_new_index_Search_ENDPOINT")
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

# 마크다운 제거 후처리
def remove_markdown(text: str) -> str:
    # 1) 헤더(# ...) 제거
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # 2) 볼드/이탤릭(*...* 또는 **...**) 제거
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    
    # 3) 언더스코어(_..._) 제거
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    
    # 4) 나머지 백틱(`) 등 제거
    text = text.replace('`', '')
    
    return text

# 최종 RAG 응답 생성 함수
def generate_answer_with_rag(query: str, source_filter: str = None, top_k: int = 3) -> str:
    results = request_ai_search(query, source_filter=source_filter, k=top_k)
    if not results:
        return "❌ 관련 문서를 찾을 수 없습니다."

    #context = "\n\n".join([f"[doc{i+1}]\n{item['content']}" for i, item in enumerate(results)])
    context = "\n\n".join([f"[{item['source']}]\n{item['content']}" for item in results])
    prompt = f"""You are an expert AI assistant. Based on the document excerpts below, answer the question in clear, concise Korean by organizing your answer into sections. Return the answer in valid JSON format using the following schema:
    
    {{
      "sections": [
        {{
          "title": "Section Title",
          "content": "Section Content"
        }},
        ...
      ]
    }}
    
    Document Excerpts:
    {context}
    
    Question:
    {query}
    
    Answer in Korean as valid JSON without using any Markdown syntax:"""
    raw_answer = request_gpt(prompt)
    # 만약 LLM의 결과에 불필요한 마크다운 문법이 남아있다면 후처리할 수 있음.
    clean_answer = remove_markdown(raw_answer)
    return clean_answer

# RAG 없이 순수 LLM만 사용해 답변 생성
def generate_answer_with_llm(query: str) -> str:
    prompt = f"""You are a professional AI assistant specializing in public policy and housing information in South Korea.

Your task is to answer the user's question clearly, **in Korean**, using accurate and up-to-date knowledge.

Instructions:
- Provide a concise answer within 300 characters.
- Use polite, reader-friendly Korean appropriate for civil service guidance.
- Do **not** use Markdown, special characters (like `#`, `*`, `_`), or emojis.
- Avoid repeating the user's question in your answer.

User's Question:
{query}

Answer (in Korean, under 300 characters):"""
    return request_gpt(prompt)

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