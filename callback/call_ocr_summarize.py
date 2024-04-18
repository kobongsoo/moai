import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from utils import generate_text_GPT2, generate_text_davinci, generate_Gemma

def call_ocr_summarize(settings:dict, data:dict, instance:dict):

    gpt_model:str = settings['GPT_MODEL']    
    system_prompt = settings['SYSTEM_PROMPT']
    
    max_tokens = settings.get('GPT_MAX_TOKENS', 1024)
    temperature = settings.get('GPT_TEMPERATURE', 1.0)
    top_p = settings.get('GPT_TOP_P', 0.1)
    stream = settings.get('GTP_STREAM', False)

    # [bong][2024-04-18] Gemma 모델 사용을 위한 설정겂 얻어
    hf_model_name = settings['HF_GEMMA_MODEL_NAME']  # 허깅페이스 Gemma 모델 명
    hf_auth_key = settings['HF_AUTH_KEY']            # 허깅페이스 사용자 모델 키
    gemma_max_tokens = settings.get('GPT_MAX_TOKENS', 1024)  # GEMMA MAX 토큰수
    
    callbackurl = data['callbackurl']
    prompt = data['prompt']
    query = data['query']
    user_id = data['user_id']
    user_mode = data['user_mode']
    prequery_embed_classification = data['pre_class'] # 회사본문검색 이전 답변 저장.(순서대로 회사검색, 웹문서검색, AI응답답변)

    # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    llm_model = data['llm_model']  
    llm_mode_str:str = gpt_model
    if llm_model == 1:
        llm_mode_str:str = hf_model_name
        
    userdb = instance['userdb']
    myutils = instance['myutils']
    prequery_embed = instance['prequery_embed']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']

    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_ocr_summarize][start]=>max_token:{max_tokens},temperature:{temperature},top_p:{top_p},stream:{stream}")
    
    start_time = time.time()

    # 프롬프트 구성
    input_prompt = prompt if prompt else query

    # [bong][2024-04-18] llm 모델 종류 1= 구글 gemma  호출
    if llm_model == 1:
        response, status = generate_Gemma(hf_model_name=hf_model_name, 
                                          prompt=input_prompt, 
                                          max_tokens=gemma_max_tokens,
                                          hf_auth_key=hf_auth_key)
    else:
        if gpt_model.startswith("gpt-"):   
            #timeout=20초면 2번 돌게 되므로 총 40초 대기함          
            response, status = generate_text_GPT2(gpt_model=gpt_model, prompt=input_prompt, system_prompt=system_prompt, 
                                                  assistants=[], stream=stream, timeout=20,
                                                  max_tokens=max_tokens, temperature=temperature, top_p=top_p) 
        else:
            response, status = generate_text_davinci(gpt_model=gpt_model, prompt=input_prompt, stream=stream, timeout=20,
                                                     max_tokens=max_tokens, temperature=temperature, top_p=top_p)

    # GPT text 생성 성공이면=>질문과 답변을 저정해둠.
    if status == 0:
        # 돌발 퀴즈를 위한 가장 마지막 질문과 답변을 저장해 둠.
        userdb.insert_quiz(userid=user_id, type=100, query=query, response=response, answer="", info="")            
    else:
        if status == 1001: # time out일때
            query = "응답 시간 초과"
            response = "⚠️AI 응답이 없습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"
        else:
            query = "응답 에러"
            response = "⚠️AI 에러가 발생하였습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"

        error = f'generate_text_xxx fail=>model:{gpt_model}'
        myutils.log_message(f'[call_ocr_summarize][error]==>call_callback:{error}=>{response}\n')

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    myutils.log_message(f"*답변: {response}")
    response = f"*AI모델:{llm_mode_str}\n\n"+response
    template = callback_template.template_ocr_summarize(query=query, response=response, elapsed_time=el_time)          

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_ocr_summarize][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    