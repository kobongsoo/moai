import os
import time
import asyncio
import threading
import httpx
import sys

def chatbot_userdoc_search(settings:dict, data:dict, instance:dict, result:dict):

    user_id = data['userid']
    query = data['query']

    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']

    # 답변 설정
    text = "🔍개인문서를 검색하고 답변 대기중..." 
    template = callback_template.usecallback_template(text=text, usercallback=True)

    # result 구조를 다른 기능과 통일시키기 위해 맟춰줌.
    result['query'] = query
    result['template'] = template

    myutils.log_message(f'\t[chatbot_userdoc_search] query:{query}')
    
    return result
    