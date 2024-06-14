import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

def call_gpt_4o_vision(settings:dict, data:dict, instance:dict):

    userdb = instance['userdb']
    myutils = instance['myutils']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']
    gpt_4o_vision = instance['gpt_4o_vision']
    
    callbackurl = data['callbackurl']
    image_path = data['query']   # 이미지 경로를 얻어옴
    user_id = data['user_id']
    user_mode = data['user_mode']

    prompt = settings['GPT_4O_VSION_PROMPT'] # 프롬프트
    
    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_gpt_4o_vision][start]=>user_mode:{user_mode},image_path:{image_path}")

    status:int = 0
    datalist:list=[]

    start_time = time.time()

    try:
        response = gpt_4o_vision.get_image_info(save_image_path=image_path, query=prompt)
    except Exception as e:
        msg = f'{e}'
        myutils.log_message(f'\t[call_music][error] {msg}')
        status = 102

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    if status == 0:
        title = "이미지 분석내용"
        template = callback_template.template_gpt_4o_vision(query=title, response=response, elapsed_time=el_time)     
        myutils.log_message(f'\t*response:\n{response}')
    else:
        text = f"⚠️AI 에러가 발생하였습니다. 잠시 후 다시 시도해 주세요.\n({status})"
        template = callback_template.simpletext_template(text=text)

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_gpt_4o_vision][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    