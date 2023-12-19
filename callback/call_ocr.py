import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from utils import generate_text_GPT2, generate_text_davinci

def call_ocr(settings:dict, data:dict, instance:dict):

    callbackurl = data['callbackurl']
    user_id = data['user_id']
    user_mode = data['user_mode']
    query = data['query']
    
    userdb = instance['userdb']
    myutils = instance['myutils']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']
    google_vision = instance['google_vision']

    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[callback_ocr][start]")
    
    start_time = time.time()

    # 이미지 OCR 텍스트 추출인 경우, 이미지에서 TEXT 추출 후 prompt 구성
    error:int = 0
    vision_url:str = query # url 저장해둠.
    
    res, error=google_vision.ocr_url(url=vision_url)
    if error == 0:
        if len(res) > 0:
            response = res[0]
            query=f"이미지에서 검출된 글자 수: {len(response)}"    
            userdb.insert_quiz(userid=user_id, type=100, query=query, response=response, answer="", info="")  # 퀴즈본문db에 저장 
        else:
            response = "⚠️이미지에서 글자를 검출 하지 못했습니다."
            query='이미지에 글자 없음..'    
    else:
        response = f"⚠️이미지에서 글자 검출 중 오류가 발생하였습니다.\n\n{res}"
        query='이미지 글자 검출시 에러..'  

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    template = callback_template.template_ocr(query=query, response=response, vision_error=error, vision_url=vision_url, elapsed_time=el_time)            

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[callback_ocr][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    