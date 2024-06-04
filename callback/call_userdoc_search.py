import os
import time
import asyncio
import threading
import httpx
import sys
import requests

from typing import Union, Dict, List, Optional

def call_userdoc_search(settings:dict, data:dict, instance:dict):   
    user_id:str = data['user_id']
    query:str = data['query']
    extra_id:str = data['extra_id']
    
    assert extra_id, f'[call_userdoc_search] extra_id is empty'
    assert query, f'[call_userdoc_search] query is empty'

    response:str = ''
    context:str = ''

    start_time = time.time()
 
    userdb = instance['userdb']
    myutils = instance['myutils']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']
    userdocmgrurl = settings['USER_DOC_MGR_URL']

    # RAG USER DOC MANAGER 서버로 쿼리 날림
    url = f"{userdocmgrurl}/search/query?user_id={extra_id}&query={query}"
    myutils.log_message(f"\t[call_userdoc_search][star]=>url:{url}")
    
    res = requests.get(url)
    myutils.log_message(f"\t[call_userdoc_search]=>res:{res}")
    myutils.log_message(f"-" * 50)

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    if res.status_code == 200:
        result = res.json()
        myutils.log_message(f"*답변: {result}")
        response = result[0]
        context = result[1]
        context = context.replace('<br>', '\n')
        myutils.log_message(f"*context 길이: {len(context)}")
    else:
        query = "응답 에러"
        response = f"⚠️AI 에러가 발생하였습니다. 잠시 후 다시 질문해 주세요.\n({res.status_code})"
        
    template = callback_template.template_userdoc_search(query=query, response=response, context=context, elapsed_time=el_time)      

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_userdoc_search][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    