from pymu import *
from azure_md import *
from azure_di import *
from table_to_text import *

# pdf_name = "LH-25년1차청년매입임대입주자모집공고문(서울지역본부).pdf"
# pdf_path = rf"{PDF_FOLDER}\{pdf_name}"
# md_file_name = ""
# md_file_path = rf"{MD_FOLDER}\{md_file_name}"

# final_text_name = ""
# final_text_path = rf"{TXT_FOLDER}\{final_text_name}"

# [PDF -> Azure DI]
def get_md_from_azure(): # for all pdf
    # ✅ 전체 처리 루프
    pdf_files = glob(os.path.join(PDF_FOLDER, "*.pdf"))
    print(f"🔍 처리할 PDF 파일 수: {len(pdf_files)}")

    for pdf_path in pdf_files:
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        blob_name = f"{filename}.pdf"
        md_path = os.path.join(MD_FOLDER, f"{filename}.md")

        print(f"\n📄 처리 중: {filename}")

        # 1. 업로드 및 SAS URL 생성
        sas_url = upload_pdf_to_blob(pdf_path, blob_name)
        print("✅ Blob 업로드 및 SAS URL 완료")

        # 2. Markdown 변환
        md_content = analyze_pdf_to_markdown(sas_url)
        print("✅ Document Intelligence 분석 완료")

        # 3. GPT 테이블 변환
        md_with_tables = convert_md_tables_with_llm_parallel(md_content)
        print("✅ GPT 테이블 변환 완료")

        # 4. 헤더 전처리
        final_md = preprocess_markdown_headers(md_with_tables)

        # 5. 저장
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_md)
        print(f"✅ 저장 완료: {md_path}")


# [PyMuPDF]
def get_md_from_pymu(pdf_path):
    # PDF data 추출
    llama_reader = pymupdf4llm.LlamaMarkdownReader()
    llama_docs = llama_reader.load_data(pdf_path)

    # 컬럼 예외처리
    cleaned_docs = []
    for doc in llama_docs:
        modified = fix_invalid_column_lines(doc.text)
        cleaned_docs.append(Document(text=modified))
    
    return cleaned_docs


# [Azure]
def edit_md_from_azure(azure_md):
    # 페이지 전처리
    restructured_pages = azure_md_preprocessing(azure_md)
    # Azure DI .md에서 연장표 index 찾기 (반례 가능성 有)
    extended_page_list = process_markdown_for_table_groups(azure_md)
    return restructured_pages, extended_page_list

# [PyMuPDF]
def get_new_table_from_pymu(cleaned_docs, extended_page_list):
    table_df_list = []

    for page_list in extended_page_list:
        full_text = merge_pagetext(cleaned_docs, page_list)
        table_list = extract_combined_tables(full_text)

        # 행이 가장 많은 표 하나만 가져오기
        max_table = max(table_list, key=count_rows)

        # 표 재구성
        merged_table_md = make_merged_table_md(max_table)
        df = make_merged_table_df(merged_table_md)

        target_df = df.ffill(axis=1).ffill(axis=0)
        table_df_list.append(target_df)

        return table_df_list

def main():
    # pdf -> azure di .md (all files)
    get_md_from_azure()

    # azure md 수정 작업 (for each file)
    pdf_files = glob(os.path.join(PDF_FOLDER, "*.pdf"))
    for pdf_path in pdf_files:
        filename = os.path.splitext(os.path.basename(pdf_path))[0]

        pdf_name = f"{filename}.pdf"
        pdf_path = rf"{PDF_FOLDER}\{pdf_name}"
        md_file_name = f"{filename}.md"
        md_file_path = rf"{MD_FOLDER}\{md_file_name}"
        final_text_name = f"{filename}.txt"
        final_text_path = rf"{TXT_FOLDER}\{final_text_name}"

        # markdown 파일 읽기
        with open("document_result.md", "r", encoding="utf-8") as file:
            azure_md = file.read()
        
        cleaned_docs = get_md_from_pymu(pdf_path)
        restructured_pages, extended_page_list = edit_md_from_azure(azure_md)
        table_df_list = get_new_table_from_pymu(cleaned_docs, extended_page_list)

        # [Azure] - Final
        final_md = replace_table_html(restructured_pages, extended_page_list, table_df_list)

        # 최종 마크다운 저장
        with open("output.md", "w", encoding="utf-8") as f:
            f.write(final_md)

        # table -> LLM -> text
        process_file(md_file_path, final_text_path)