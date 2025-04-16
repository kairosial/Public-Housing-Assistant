from config import *
import json


def save_pdf_to_json(filename, sas_url: str) -> str:
    """Document Intelligence를 사용해 JSON으로 변환"""
    poller = di_client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(url_source=sas_url)
    )
    result = poller.result()

    output_data = {
    "pages": [],
    }

    for page_idx, page in enumerate(result.pages):
        page_data = {
        "pageNumber": page_idx + 1,
        "lines": []
        }

        for line_idx, line in enumerate(page.lines):
            line_data = {
                "content": line.content,
                "polygon": [
                    point for point in line.polygon
                ]
            }
            page_data["lines"].append(line_data)

        output_data["pages"].append(page_data)
    

    # json_path = os.path.join(JSON_FOLDER, f"{filename}.json")

    # with open(json_path, 'w', encoding="utf-8") as f:
    #     json.dump(output_data, f, ensure_ascii=False, indent=4)    
    
    # print(f"✅ 저장 완료: {json_path}")

    return output_data

