import re
from difflib import SequenceMatcher
from config import *
from heading.extract_title import find_symbols


def add_bool_data(header_list):
    for key, _ in header_list.items():
        if isinstance(header_list[key], list):
            header_list[key].append(False)
        else:
            header_list[key] = [header_list[key], False]
    return header_list

# 라인 간 유사도 계산
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

# 대/중/소제목별 Markdown 제목 수준 출력
def match_header_level(heading_list, content):
    headers = heading_list[content]
    if headers[0] == "mainTitle":
        headers[1] = True
        return f'# '
    elif headers[0] == "subTitle":
        headers[1] = True
        return f"## "
    elif headers[0] == "subHeading":
        headers[1] = True
        return f"### "

# 추출된 제목 데이터 기준으로 Markdown 파일의 제목 변환
def convert_heading_md(md_path, md_content, header_list):

    header_list = add_bool_data(header_list)

    # # 읽기
    # with open(md_path, "r", encoding="utf-8") as f:
    #     lines = f.readlines()

    # 변환
    converted_lines = []
    for line in md_content:
        if "td>" in line or "tr>" in line or find_symbols(line):
            converted_lines.append(line)
            continue
            
        if '#' in line:
            line = line.lstrip("#").strip()
        
        if "<!-- PageHeader=" in line:
            result = re.search(r'PageHeader="(.*?)"', line)
    
            if result:
                line = result.group(1)
        # print(line)
        
        for content in header_list:
            score = similarity(line, content)
            if score >= 0.8 and header_list.get(content)[1] == False:
                # print(f'score: {score}', line, content, '\n')
                header = match_header_level(header_list, content)
                converted_lines.append(header)
        else:
            converted_lines.append(line)
    
    # # 저장
    # file_path, file_name = os.path.split(md_path)
    # new_file_path = os.path.join(file_path, 'processed')
    # os.makedirs(new_file_path, exist_ok=True)
    # output_path = os.path.join(new_file_path, 'proc_' + file_name)
    
    # with open(output_path, "w", encoding="utf-8") as f:
    #     f.writelines(converted_lines)
        
    # print(f'✅ 저장 완료: {output_path}')

    return converted_lines