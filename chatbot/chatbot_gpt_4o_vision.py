import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

#sys.path.append('..')
#from vision import GPT_4O_VISION

def chatbot_gpt_4o_vision_save_image(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; error:int=0

    content = data['userRequest']
    user_id = data['userid']
           
    assert user_id, f'user_id is empty'

    myutils = instance['myutils']
    id_manager = instance['id_manager']
    gpt_4o_vision = instance['gpt_4o_vision']
    
    callback_template = instance['callback_template']

    image_url = content['params']['media']['url']
    myutils.log_message(f'\t[chatbot_gpt_4o_vision_save_image]==>image_url:{image_url}')

    # URL 이미지를 다운로드 해서 사이즈 줄이고 저장해 둠.
    image_path = gpt_4o_vision.download_and_save_image(url=image_url)
    myutils.log_message(f'\t[chatbot_gpt_4o_vision_save_image]==>image_path:{image_path}')

    if image_path:
        search_str = "🧮이미지 분석중 입니다.."
        template = callback_template.usecallback_template(text=search_str, usercallback=True)
    else:
        id_manager.remove_id_all(user_id) # id 제거
        text = "⚠️이미지 분석에 실패하였습니다. 잠시후 다시 시도해 주세요."
        template = callback_template.simpletext_template(text = text)
        result['error'] = 1002

    result['query'] = image_path  # 이미지 경로를 저장해 둠.
    result['template'] = template

    
    return result
    
    