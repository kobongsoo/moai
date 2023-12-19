import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def chatbot_url_summarize(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0
    
    user_id = data['userid']
    query = data['query']
    
    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:]  
        
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    webscraping = instance['webscraping']
    myutils = instance['myutils']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']

    SCRAPING_WEB_MAX_LEN = settings['SCRAPING_WEB_MAX_LEN']
    prompt_summarize:str = settings['PROMPT_URL_SUMMARIZE']  # [2023-12-11] 요약 명령 프롬프트 
    
    context, error = webscraping.scraping_web(url=query)
    if len(context) > 300:
        if len(context) > SCRAPING_WEB_MAX_LEN:
            context = context[0:SCRAPING_WEB_MAX_LEN-1]
            
        prompt = f'{context}\n\nQ:{prompt_summarize}'
        search_str = "💫URL 내용 요약중.."
        template = callback_template.usecallback_template(text=search_str, usercallback=True)
    else:
        if len(context) == 0:
            answer = f"⚠️URL 검출된 내용이 없습니다..URL을 다시 입력해주세요."
        elif len(context) < 301:
            answer = f"⚠️URL 검출된 내용이 너무 적어서 요약할 수 없습니다.. (길이:{len(context)})\n내용:\n{context}"
        else:
            answer = f"⚠️URL 내용 검출 실패..URL을 다시 입력해주세요.\n(error:{error})"
            
        template = callback_template.simpletext_template(text=answer)
            
        # id_manager 에 id 제거
        # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
        id_manager.remove_id_all(user_id) # id 제거
       
    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
        
    return result
    
    