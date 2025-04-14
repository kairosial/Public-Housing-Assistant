from config import *

def fix_invalid_column_lines(md_text: str) -> str:
    lines = md_text.splitlines()
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 조건: | 2개 이상 + 특수기호 포함 + 다음줄 구분선 + 다다음 줄 존재
        if (
            line.count('|') >= 2 and 
            any(char in line for char in special_chars) and 
            i + 2 < len(lines)
        ):
            next_line = lines[i + 1].strip()
            next_next_line = lines[i + 2].strip()

            if re.fullmatch(r'\|?[-| ]+\|?', next_line):
                print("컬럼 순서 변경:", line)

                # 잘못된 줄 (| 제거) 먼저 올림
                new_lines.append(line.replace('|', '').strip())
                # 실제 컬럼명
                new_lines.append(next_next_line)
                # 구분선
                new_lines.append(next_line)

                i += 3
                continue

        # 그 외는 그대로
        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines)

def merge_pagetext(docs, page_list):
    merged_text = ""
    for page in page_list:
        text = docs[page-1].text
        merged_text += text
    merged_text = merged_text.replace('-----', '') #  페이지 구분 선

    # 페이지 넘버 문자열 제거
    for page_num in page_list:
        merged_text = merged_text.replace(f"- {page_num}", '')

    return merged_text

def is_table_separator(line):
    return re.match(r'^\s*\|?[:\-]+(?:\|[:\-]+)*\|?\s*$', line.strip())

def is_table_row(line):
    return re.match(r'^\s*\|.*\|\s*$', line.strip())

def is_ignore_line(line):
    # 페이지 나눔 같은 구분선: -----, =====, *** 등
    return re.match(r'^\s*[-=*]{3,}\s*$', line.strip())

def extract_combined_tables(text):
    lines = text.splitlines()
    tables = []
    current_table = []
    inside_table = False
    is_column = False

    for line in lines:
        if is_table_row(line) or is_table_separator(line):
            current_table.append(line.strip())
            inside_table = True
        elif is_ignore_line(line):
            # 페이지 구분 등은 무시하고 표 계속 이어붙임
            continue
        elif line.strip() == '':
            # 빈 줄은 무시 (표 끊지 않음)
            continue
        else:
            # 일반 텍스트: 표 끝으로 간주
            if inside_table and current_table:
                tables.append('\n'.join(current_table))
                current_table = []
                inside_table = False

    # 끝에 표가 남아 있다면 추가
    if current_table:
        tables.append('\n'.join(current_table))

    return tables

# 행 수 세는 함수 (헤더 제외, 구분선 제외)
def count_rows(md_table):
    lines = md_table.strip().splitlines()
    return max(0, len(lines) - 2)

# 마크다운 테이블 재구성 함수
def make_merged_table_md(merged_text):

    # 각 줄 단위로 분리
    lines = merged_text.strip().split('\n')

    # 첫 번째 컬럼만 헤더 공백값 전처리
    lines[0] = lines[0].replace('||', '|Col|')

    # 여기서 지우자 잘못 들어간 구분선
    

    # 결과를 저장할 리스트
    merged_table = []
    merged_table.extend(lines[:2])
    header_found = True
    for i in range(2, len(lines)):
        line = lines[i]
        # print(line)
        if '|---|' in line:
            merged_table.pop()
            line = ''

        if line == '':
            continue
        if re.match(r'^\|.*\|$', line.strip()):
            # 헤더가 아직 발견되지 않았다면 첫 헤더와 구분선만 추가
            if not header_found and re.match(r'^\|[^|]+\|[^|]+\|*', line):
                merged_table.append(line)
                header_found = True
            # 구분선은 무시 (두 번째 이후는)
            elif '---' in line:
                continue
            else:
                # 나머지는 데이터 행으로 처리
                merged_table.append(line)

    # 결과 출력 (마크다운 표 형태)
    return '\n'.join(merged_table)

# 마크다운 테이블 재구성 함수
def make_merged_table_df(merged_text):
    # table_blocks = re.findall(r'(\|.*?\|\n(\|[-:]+[-|:]*\|\n)(\|.*?\|\n)+)', merged_text, re.DOTALL)
    # first_block = table_blocks[0]
    # table_md = first_block[0]
    # rows = table_md.strip().split("\n")

    rows = merged_text.strip().split("\n")
    header = rows[0]  # 컬럼명 (첫 번째 행)
    column_list = [col.strip() for col in header.split("|") if col.strip()]
    data_rows = rows[2:]

    df = pd.read_csv(StringIO("\n".join([header] + data_rows)), sep="|", engine="python", skipinitialspace=True)
    df = df.iloc[:, 1:-1]  # 앞뒤 공백 컬럼 제거
    df.columns = column_list 
    df = df[0:].reset_index(drop=True)  # 데이터만 유지

    # ffill은 따로 해주기 (병합셀 심화 과정- 함수 안에서 하거나 반환한 테이블 전처리 따로)
    return df