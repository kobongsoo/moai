import os
import random
import numpy as np
from typing import Dict, List, Optional
import time
import re

def remove_query_number_text(input_text):
    # 정규표현식을 사용하여 "[문제"와 "] " 사이의 숫자를 추출
    matches = re.findall(r'\[문제(\d+)\]', input_text)

    # 숫자를 갖고 있는 "[문제]" 패턴이 있을 경우 첫 번째 매치만 사용
    if matches:
        first_match = matches[0]
        modified_text = re.sub(rf'\[문제{first_match}\]', '[문제]', input_text)
        return modified_text

    # 숫자를 갖고 있는 "[문제]" 패턴이 없을 경우 원본 문자열 반환
    return input_text
    
def quiz_parser(input_text:str):
    
    quizzes:list=[]
    
    try:
        # 문단으로 구분
        texts = re.split(r'\n\n', input_text)
        for text in texts:
            text += '\n'
            text = remove_query_number_text(text)
            
            query:str=''; answer:str=''; info:str=''
            
            # 정규표현식을 사용하여 [문제1] 문장과 1, 2, 3, 4 항목 추출
            pattern = r"\[문제\](.*?)\["
            match = re.search(pattern, text, re.DOTALL)

             # 정규표현식을 사용하여 1. 문장과 1, 2, 3, 4 항목 추출(*[문제] 문자열이 없는 경우)
            if match == None:
                pattern = r"(.*?)\["
                match = re.search(pattern, text, re.DOTALL)
        
            if match:
                query = match.group(1).strip()
                pattern = r"답\](.*?)\["
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    answer = match.group(1).strip()
                    pattern = r"\[설명\](.*?)\n"
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        info = match.group(1).strip()
    
            data:dict={}
            data['query'] = query
            data['answer'] = answer
            data['info'] = info
        
            quizzes.append(data)
        
        return quizzes
    except Exception as e:
        print(f'[error]quiz_parser=>{e}')
        return []    
    