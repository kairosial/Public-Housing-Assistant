from config import *

def process_file(input_file_path, output_file_path=None):
    """
    Process an input file through Azure AI to convert HTML tables to text.
    """
    load_dotenv()
    endpoint = os.getenv("OPENAI_ENDPOINT")
    deployment = os.getenv("embedding_deployment")
    subscription_key = os.getenv("OPENAI_API_KEY")
    
    if not all([endpoint, deployment, subscription_key]):
        raise ValueError("환경변수 누락: ENDPOINT_URL, DEPLOYMENT_NAME, AZURE_OPENAI_KEY를 확인하세요.")
    
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2024-05-01-preview",
    )
    
    with open(input_file_path, 'r', encoding='utf-8') as file:
        input_content = file.read()
    
    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "너는 HTML 테이블을 읽고 자연스러운 서술형 텍스트로 변환하는 텍스트 변환 엔진이다.\n\n입력 데이터는 일반 텍스트와 HTML 코드가 혼합된 문서이며, 이 중 HTML 테이블(`<table>`) 형식으로 작성된 표만을 감지하여 사람이 읽기 쉬운 **자연스러운 텍스트**로 변환하라. 표 외의 일반 텍스트는 **절대로 변경하지 않는다**. \n\n출력된 텍스트는 아래의 기준을 모두 따라야 한다:\n\n1. 표의 계층 구조, 제목, 셀의 관계를 모두 파악하여 자연어로 기술한다.\n2. 셀이 병합된 경우 (`rowspan`, `colspan`)에는 의미적으로 내용을 통합하여 풀어서 설명한다.\n3. 표 안에 또 다른 표가 중첩되어 있는 경우에도 각 표를 계층적으로 처리하고, 문맥상 자연스럽게 연결되도록 한다.\n4. 빈 칸이 있는 경우, 내용을 유추하지 않고 \"(빈칸)\" 또는 \"해당 없음\" 등으로 명확하게 표기한다.\n5. 항목 간 구분은 \"■\", \"1.\", \"-\" 등을 사용하여 명확히 구분하고, 계층적으로 정리한다.\n6. 결과 텍스트는 반드시 문맥상 자연스럽고 일관되게 연결되어야 하며, 원래 문서의 흐름과 연결되도록 이어져야 한다.\n7. HTML 태그가 아닌 일반 텍스트 영역은 절대로 수정하거나 재구성하지 않는다.\n8. 결과는 마크다운 문서로 사용 가능한 수준의 가독성을 갖춰야 하며, 표를 설명하는 문장은 공식 문서나 계약서 스타일처럼 명료하고 단정하게 작성한다.\n\n예외나 애매한 구조가 있어도 최대한 의미를 보존하여 사람이 이해할 수 있도록 직관적으로 설명하라.\n\n입력 형식 예시:\n(본문 텍스트)\n<table>...</table>\n(본문 텍스트 계속)\n\n출력 형식 예시:\n(본문 텍스트)\n■ 항목명  \n- 내용1  \n- 내용2  \n이제 아래에 입력된 문서 내 HTML 테이블을 위 기준에 따라 서술형 텍스트로 변환하라."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": input_content
                }
            ]
        }
    ]
    
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_tokens=1500,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stream=False
    )
    
    processed_text = completion.choices[0].message.content
    
    if not output_file_path:
        base, _ = os.path.splitext(input_file_path)
        output_file_path = f"{base}_processed.txt"
    
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(processed_text)
    
    print(f"✅ 변환 완료: {output_file_path}")
    return processed_text