from pymu import *
from azure_md import *
from azure_di import *
from config import *
from table_to_text import *
from heading.azure_di_json import *
from heading.extract_title import extract_heading_from_json
from heading.replace_md import convert_heading_md

SUBHEADING_PARAM = 90
SUBTITLE_PARAM = 95

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
    # for _ in range(1):
    #     filename = os.path.splitext(os.path.basename(pdf_files[0]))[0]

        blob_name = f"{filename}.pdf"
        md_path = os.path.join(MD_FOLDER, f"{filename}.md")
        new_md_path = os.path.join('data/new_markdown', f"{filename}.md")
        proc_md_path = os.path.join('data/new_markdown/processed', f"proc_{filename}.md")
        print(proc_md_path)
        print(f"\n📄 처리 중: {filename}")
        '''
        # 1. 업로드 및 SAS URL 생성
        sas_url = upload_pdf_to_blob(pdf_path, blob_name)
        print("✅ Blob 업로드 및 SAS URL 완료")
        
        # 2. Markdown 변환
        md_content = analyze_pdf_to_markdown(sas_url)
        print("✅ Document Intelligence(md) 분석 완료")
        
        # 3. JSON에서 헤더 정보 추출 및 Markdown 헤더 변환 
        json_file = save_pdf_to_json(filename, sas_url)
        header_list = extract_heading_from_json(json_file, SUBHEADING_PARAM, SUBTITLE_PARAM)
        proc_title_md = convert_heading_md(new_md_path, md_content, header_list)
        print("✅ 헤더 추출 및 변환 완료")
        '''
        # 읽기
        with open(proc_md_path, "r", encoding="utf-8") as f:
            md_file = f.read()

        # 4. GPT 테이블 변환
        md_with_tables = convert_md_tables_with_llm_parallel(md_file)
        print("✅ GPT 테이블 변환 완료")
        
        # # 4. 헤더 전처리
        # final_md = preprocess_markdown_headers(md_with_tables)

        # 5. 저장
        final_path = os.path.dirname(proc_md_path)
        final_path = os.path.join(final_path, 'processed_gpt', f'fin_{filename}.md')
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(md_with_tables)
        print(f"✅ 저장 완료: {final_path}")
        
        

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

    # 현재 파일을 실행한 경로로 이동
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    os.chdir(current_dir)

    # pdf -> azure di .md (all files)
    get_md_from_azure()
    
    '''
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
        # with open("document_result.md", "r", encoding="utf-8") as file:
        with open(md_file_path, "r", encoding="utf-8") as file:
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
        '''

if __name__ == '__main__':
    main()