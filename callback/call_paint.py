import time
import httpx
import sys

from typing import Union, Dict, List, Optional

def call_paint(settings:dict, data:dict, instance:dict):

    callbackurl = data['callbackurl']
    query = data['query']
    user_id = data['user_id']
    user_mode = data['user_mode']
 
    userdb = instance['userdb']
    myutils = instance['myutils']
    prequery_embed = instance['prequery_embed']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']
    translator = instance['translator']
    karlo = instance['karlo']
    
    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_paint][start]=>query:{query}")
    
    start_time = time.time()

    # 입력된 쿼리를 영문으로 번역
    res = translator.translate(text=query, src='ko', dest='en')
    prompt = res.text.strip('"')

    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_paint]번역:{prompt}")

    # 이미지 생성하기 REST API 호출
    response = karlo.text2image(prompt=prompt, negative_prompt="")

    image_url:str = ""
    try:
        if response:
            image_url = response['images'][0]['image']
    except Exception as e:
        msg = f'{error}=>{e}'
        myutils.log_message(f'[error] {msg}')
        
    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    myutils.log_message(f"*답변: {image_url}")
    template = callback_template.template_paint(query=query, image_url=image_url, elapsed_time=el_time)      

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_paint][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template