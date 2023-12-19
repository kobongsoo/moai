import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def chatbot_web_search(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0

    user_id = data['userid']
    query = data['query']
    search_site = data['search_site']

    assert user_id, f'user_id is empty'
    assert query, f'query is empty'
    
    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:] 
        
    gpt_model = settings['GPT_MODEL']
    
    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']
    
    naver_api = instance['naver_api']
    google_api = instance['google_api']
    
    # 1=네이버 검색
    error:int = 0; s_context:str = ''; s_best_contexts:list = []; prompt:str=''; s_contexts:list = []; s_str:str = "네이버"
    
    try:
        if search_site == "naver":
            # 네이버 검색
            classification=['news', 'webkr', 'blog']
            # 랜덤하게 2개 선택
            #selected_items = random.sample(classification, 2)
            #random.shuffle(classification)  #랜덤하게 3개 섞음
            #start=random.randint(1, 2)
            s_contexts, s_best_contexts, s_error = naver_api.search_naver(query=query, classification=classification, start=1, display=6)
        else: # 구글 검색
            s_contexts, s_best_contexts, s_error = google_api.search_google(query=query, page=2) # page=2이면 20개 검색
            s_str = "구글"
                
    except Exception as e:
        myutils.log_message(f'\t[chatbot3]==>naver_api.search_naver fail=>{e}')
        # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
        id_manager.remove_id_all(user_id) # id 제거
        result['error'] = 1001
        
    # prompt 구성
    if len(s_contexts) > 0 and s_error == 0:
        for idx, con in enumerate(s_contexts):
            if con['descript'] and con['title']:
                s_context += f"{con['title']}\n{con['descript']}\n\n"
                               
        # text-davinci-003 모델에서, 프롬프트 길이가 총 1772 넘어가면 BadRequest('https://api.openai.com/v1/completions') 에러 남.
        # 따라서 context 길이가 1730 이상이면 1730까지만 처리함.
        if gpt_model.startswith("text-") and len(s_context) > 1730:
            s_context = s_context[0:1730]

        prompt = settings['PROMPT_CONTEXT'].format(context=s_context, query=query)
        search_str = f"🔍{s_str}검색 완료. 답변 대기중.."
    else:
        prompt = settings['PROMPT_NO_CONTEXT'].format(query=query)  
        search_str = f"🔍{s_str}검색 없음. 답변 대기중.."

    template = callback_template.usecallback_template(text=search_str, usercallback=True)

    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
    result['s_best_contexts'] = s_best_contexts
        
    return result
    
    