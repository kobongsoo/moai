import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def chatbot_chatting(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0
    
    user_id = data['userid']
    query = data['query']

    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:] 
        
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    callback_template = instance['callback_template']
    
    prompt = settings['PROMPT_NO_CONTEXT'].format(query=query)  
    search_str = "🤖AI 답변 준비중.."
    template = callback_template.usecallback_template(text=search_str, usercallback=True)

    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
        
    return result


    
    
    
    