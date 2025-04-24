from config import *

def azure_md_preprocessing(azure_md):
    """
    azure md bullet 및 예외 데이터 전처리, 계층구조 삭제
    ---
    params: 애져 마크다운 텍스트
    ---
    return: 전처리된 마크다운 텍스트를 페이지별로 나눈 리스트 
    """
    # 페이지 분할: 페이지 번호와 내용을 그룹으로 가져오기
    split_pages = re.split(r'<!--\s*PageNumber="([^"]*)"\s*-->', azure_md)

    # 불필요한 처음 항목 제거 (페이지 번호 앞 텍스트)
    if split_pages and not split_pages[0].strip():
        split_pages = split_pages[1:]

    # 페이지 목록을 (페이지번호, 내용) 튜플로 묶기
    page_pairs = list(zip(split_pages[::2], split_pages[1::2]))

    # 전처리 및 페이지 재조합
    restructured_pages = []

    for page_number, content in page_pairs:
        lines = content.splitlines()
        new_lines = []

        for line in lines:
            if "■" in line:
                # 동작1: '#' 등 마크다운 계층 구조 제거
                cleaned_line = re.sub(r'^[#>\-\*\s]+', '', line)
                # 동작2: ■ 앞에 공백이 있다면 \n■ 처리
                cleaned_line = re.sub(r'\s*■', r'\n■', cleaned_line)
                # 동작3: ':'가 있다면 \n: 처리
                cleaned_line = re.sub(r'\s* :\s*', r'\n:', cleaned_line)
                # 동작4: ") " → ")\n"
                cleaned_line = re.sub(r'\)\s+', r')\n', cleaned_line)
                new_lines.append(cleaned_line)
            else:
                new_lines.append(line)

        # 전처리된 페이지 내용 조합
        modified_content = '\n'.join(new_lines)
        # page_comment = f'<!-- PageNumber="{page_number.strip()}" -->'
        restructured_pages.append(f"{page_number.strip()}")

        return restructured_pages

def split_pages(markdown_text):
    pattern = r'<!-- PageNumber="- (\d+) -" -->\s*<!-- PageBreak -->'
    parts = re.split(pattern, markdown_text)
    pages = []
    for i in range(1, len(parts), 2):
        page_num = int(parts[i]) + 1
        content = parts[i+1].strip()
        pages.append((page_num, content))
    return pages

def is_table_only(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text().strip()
    # 태그 중 table 관련 태그만 있는지 확인
    allowed_tags = {'table', 'tr', 'td', 'th'}
    all_tags = {tag.name for tag in soup.find_all()}
    return (text == '') and all_tags.issubset(allowed_tags)

def detect_table_transition(pages):
    transitions = []
    page_unit = []
    for i in range(len(pages) - 1):
        
        curr_page_num, curr_content = pages[i]
        next_page_num, next_content = pages[i + 1]

        if curr_content.strip().endswith('</table>') and next_content.strip().startswith('<table>'): # 현 페이지가 </table>로 끝나고 다음 페이지가 <table>로 시작할 때
            if curr_page_num in page_unit: # 이미 페이지가 page_unit에 있다면
                if curr_content.strip().startswith('<table>') and curr_content.strip().endswith('</table>'):
                    if len(curr_content.split('</table>')) > 2: # 현재 페이지 안에 표가 2개 이상
                        transitions.append(page_unit) # 현재 페이지까지 저장된 unit 저장
                        page_unit = []
                        page_unit.append(curr_page_num) # 현재 페이지부터 다시 카운트
                        page_unit.append(next_page_num)
                    else:
                        page_unit.append(next_page_num) # 한 페이지 전체가 표. 다음 페이지만 저장
                else:
                    transitions.append(page_unit)
                    page_unit = []
                    page_unit.append(curr_page_num)
            else:
                if page_unit:
                    transitions.append(page_unit)
                    page_unit = []
                page_unit.append(curr_page_num)
                page_unit.append(next_page_num)
                
    transitions.append(page_unit)
    return transitions

def merge_transitions(transitions, pages_dict):
    if not transitions:
        return []

    merged = []
    current_group = transitions[0]

    for next_pair in transitions[1:]:
        prev_last = current_group[-1]
        next_first = next_pair[0]

        if prev_last == next_first:
            # 중간 페이지가 table-only이면 병합
            if is_table_only(pages_dict[prev_last]):
                current_group.append(next_pair[1])
            else:
                merged.append(current_group)
                current_group = next_pair
        else:
            merged.append(current_group)
            current_group = next_pair

    merged.append(current_group)
    return merged

def process_markdown_for_table_groups(markdown_text):
    pages = split_pages(markdown_text)
    pages_dict = dict(pages)
    transitions = detect_table_transition(pages)
    merged_groups = merge_transitions(transitions, pages_dict)
    return merged_groups

def replace_table_html(restructured_pages, extended_page_list, table_df_list):
    # 전처리 및 페이지 재조합
    pattern = re.compile(r'<table[\s\S]*?</table>', re.IGNORECASE)

    for i in range(len(extended_page_list)):
        page_list = extended_page_list[i]
        df = table_df_list[i]
        new_html_table = df.to_html(index=False, escape=False)

        # 첫 페이지
        first_page = page_list[0]
        page_md = restructured_pages[first_page-1]
        matches = list(pattern.finditer(page_md))
        matched_table = matches[-1].group()
        new_page_md = page_md.replace(matched_table, new_html_table)
        restructured_pages[first_page-1] = new_page_md

        # 마지막 페이지 + 나머지
        for i in range(1, len(page_list)):
            page_md = restructured_pages[page_list[i]-1]
            matches = list(pattern.finditer(page_md))
            matched_table = matches[0].group()
            new_page_md = page_md.replace(matched_table, '')
            restructured_pages[page_list[i]-1] = new_page_md
    
    final_md = '\n'.join(restructured_pages)
    return final_md