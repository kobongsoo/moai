import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def chatbot_ocr(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0

    content = data['userRequest']
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

    if prefix_query == '@':  # 이미지에서 글자다시 검출인경우..
        ocr_url = query
    else:
        ocr_url = content['params']['media']['url']
        
    search_str = "📷이미지에서 글자 검출중.."
    template = callback_template.usecallback_template(text=search_str, usercallback=True)
    
    result['query'] = query
    result['template'] = template

    return result
    
    