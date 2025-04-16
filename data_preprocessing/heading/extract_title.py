import numpy as np
import re


# 문단 구분 기호 존재 확인
def find_symbols(contents):
    symbols = "●◎■"
    pattern = rf"^[{symbols}]\s?.*"    
    return re.search(pattern, contents, re.MULTILINE) is not None


# BoundingBox의 polygon값 계산
def get_polygon_indent(polygon):
    x_values = [polygon[i] for i in range(0, len(polygon), 2)]
    return min(x_values)

def get_polygon_height(polygon):
    y_values = [polygon[i+1] for i in range(0, len(polygon), 2)]
    return max(y_values) - min(y_values)

def get_polygon_width(polygon):
    x_values = [polygon[i] for i in range(0, len(polygon), 2)]
    return max(x_values) - min(x_values)


# 전체 페이지 탐색하여 최적의 글자 크기, 들여쓰기 값 찾기
def find_optim_values(pages, param):
    indents = list()
    heights = list()

    for i in range(len(pages)):
        lines = pages[i]['lines']

        for j in range(len(lines)):
            # height
            height = get_polygon_height(lines[j]['polygon'])
            heights.append(height)

            indent = get_polygon_indent(lines[j]['polygon'])
            indents.append(indent)
        
    std_indent = np.percentile(indents, param)
    std_height = np.percentile(heights, param)

    return std_indent, std_height


# JSON 파일의 polygon 값으로 제목 추출 
def extract_heading_from_json(json_file, param1, param2):

    pages = json_file['pages']
    std_indent, std_height = find_optim_values(pages, param1)
    print(std_indent, std_height)

    heights = list()
    headings = dict()

    for i in range(len(pages)):
        lines = pages[i]['lines']

        for j in range(len(lines)):

            polygon = lines[j].get('polygon')
            content = lines[j].get('content')
            role = lines[j].get('role')
            
            # indent
            indent = get_polygon_indent(polygon)
            height = get_polygon_height(polygon)

            
            if find_symbols(content):
                if indent < std_indent and height > std_height:
                    if not 'role' in lines[j]:
                        lines[j]['role'] = None

                    role = 'subHeading'
                    heights.append(height)            
                    headings[content] = 'subHeading'
            else:
                continue
            
    try:
        title_height = np.percentile(heights, param2)
    except:
        try:
            title_height = np.percentile(heights, 90)
        except:
            title_height = np.percentile(heights, 80)
        
    for i in range(len(pages)):
        lines = pages[i]['lines']

        for j in range(len(lines)):

            polygon = lines[j].get('polygon')
            content = lines[j].get('content')
            role = lines[j].get('role')

            # height
            height = get_polygon_height(polygon)
            width = get_polygon_width(polygon)

            if role != 'subHeading':
                if title_height * 1.5 > height > title_height and width > 0.5:
                    headings[content] = 'subTitle'
                    # print(content, role, height, width, sep=' / ')   

                elif 0.5 > height >= title_height * 1.5 and width > 0.5:
                    headings[content] = 'mainTitle'
                    # print(content, role, height, width, sep=' / ')                     
    return headings
