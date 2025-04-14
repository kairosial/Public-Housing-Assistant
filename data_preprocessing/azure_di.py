from config import *

def upload_pdf_to_blob(pdf_path: str, blob_name: str) -> str:
    """PDF를 Blob에 업로드하고 SAS URL 반환"""
    blob_client = container_client.get_blob_client(blob_name)
    with open(pdf_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=True)

    sas_token = generate_blob_sas(
        account_name=blob_service.account_name,
        container_name=BLOB_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=blob_service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=15)
    )

    return f"{blob_client.url}?{sas_token}"


def analyze_pdf_to_markdown(sas_url: str) -> str:
    """Document Intelligence를 사용해 Markdown으로 변환"""
    poller = di_client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(url_source=sas_url),
        output_content_format='markdown'
    )
    result = poller.result()
    return result.content


def request_gpt(prompt: str) -> str:
    headers = {
        'Content-Type': 'application/json',
        'api-key': gpt_api_key
    }
    body = {
        "messages": [
            {
                "role": "system",
                "content": (
                    '너는 HTML 테이블을 사람이 이해할 수 있도록 자연어 문장으로 변환해.  '
                    '항목과 값을 "구분: 내용" 식으로 나누지 말고, 원래 테이블에서 쓰인 항목명을 그대로 key로 사용해.  '
                    '예: "임대조건 : 내용", "임대보증금-월임대료 전환 : 내용"처럼.  '
                    '항목이 반복되는 경우에는 구분자를 붙여서 명확하게 구분해줘.  '
                    '불필요한 요약이나 도입부 없이 표의 핵심 내용만 변환해줘.'
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(gpt_endpoint, headers=headers, json=body)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print("❌ 요청 실패:", response.status_code, response.text)
        return "⚠️ 오류가 발생했습니다."


def convert_md_tables_with_llm_parallel(md_text: str, max_workers=5) -> str:
    soup = BeautifulSoup(md_text, 'html.parser')
    tables = soup.find_all('table')
    table_strs = [str(table) for table in tables]
    unique_tables = list(set(table_strs))
    table_to_text = {}

    def process_table(table_html):
        prompt = (
            f"다음 HTML 테이블의 내용을 자연어 문장으로 간결하게 변환해줘.\n\n{table_html}"
        )
        result = request_gpt(prompt)
        return table_html, result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_table, tbl) for tbl in unique_tables]
        for future in as_completed(futures):
            tbl_html, gpt_result = future.result()
            table_to_text[tbl_html] = gpt_result

    for original_table in table_strs:
        if original_table in table_to_text:
            md_text = md_text.replace(original_table, table_to_text[original_table])

    return md_text


def preprocess_markdown_headers(md_text: str) -> str:
    md_text = re.sub(r'^(#{1,6}\s*■?\s*[^:\n]+):\s*(.+)$', r'\1\n\2', md_text, flags=re.MULTILINE)
    md_text = re.sub(r'^(■\s*\([^)]+\))\s+(.+)$', r'\1\n\2', md_text, flags=re.MULTILINE)
    return md_text
