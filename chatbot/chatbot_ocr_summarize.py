import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def chatbot_ocr_summarize(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0

    user_id = data['userid']
    query = data['query']

    prompt_summarize:str = settings['PROMPT_OCR_SUMMARIZE']  # [2023-12-11] 요약 명령 프롬프트 
    
    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:]  
        
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    webscraping = instance['webscraping']
    myutils = instance['myutils']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']
    userdb = instance['userdb']

    context:str = ''
    res, quiz_num = userdb.select_quiz(userid=user_id, type=100) # 저장된 최근 response를 얻어옴.
    if res != -1:
        if len(res) > 0:
            context = res[0]['response']
            
    prompt = f'{context}\n{prompt_summarize}' 
    search_str = "🎞이미지 내용 요약중.."
    query = "📷이미지 내용 요약 결과.."
    
    template = callback_template.usecallback_template(text=search_str, usercallback=True)

    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
        
    return result
    
    