import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from utils import generate_text_GPT2, generate_text_davinci

def call_chatting(settings:dict, data:dict, instance:dict):
    
    gpt_model:str = settings['GPT_MODEL']    
    system_prompt = settings['SYSTEM_PROMPT']

    max_tokens = settings.get('GPT_MAX_TOKENS', 1024)
    temperature = settings.get('GPT_TEMPERATURE', 1.0)
    top_p = settings.get('GPT_TOP_P', 0.1)
    stream = settings.get('GTP_STREAM', False)

    callbackurl = data['callbackurl']
    prompt = data['prompt']
    query = data['query']
    user_id = data['user_id']
    user_mode = data['user_mode']
    prequery_embed_classification = data['pre_class'] # 회사본문검색 이전 답변 저장.(순서대로 회사검색, 웹문서검색, AI응답답변)

    userdb = instance['userdb']
    myutils = instance['myutils']
    prequery_embed = instance['prequery_embed']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']

    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_chatting][start]=>max_token:{max_tokens},temperature:{temperature},top_p:{top_p},stream:{stream}")
    
    start_time = time.time()

    # 프롬프트 구성
    input_prompt = prompt if prompt else query
                
    if gpt_model.startswith("gpt-"):
        preanswer_list:list = []
        # 채팅 일대만 이전 GPT 답변 목록 얻어옴
        preanswers = userdb.select_assistants(user_id=user_id)
        if preanswers != -1:
            for preanswer in reversed(preanswers):  # 역순으로 저장해둠.
                if preanswer['preanswer']:
                    preanswer_list.append(preanswer['preanswer'])
                    
        #timeout=20초면 2번 돌게 되므로 총 40초 대기함
        response, status = generate_text_GPT2(gpt_model=gpt_model, prompt=input_prompt, system_prompt=system_prompt, 
                                              assistants=preanswer_list, stream=stream, timeout=20,
                                              max_tokens=max_tokens, temperature=temperature, top_p=top_p) 
    else:
        response, status = generate_text_davinci(gpt_model=gpt_model, prompt=input_prompt, stream=stream, timeout=20,
                                                 max_tokens=max_tokens, temperature=temperature, top_p=top_p)

    # GPT text 생성 성공이면=>질문과 답변을 저정해둠.
    if status == 0:
        # 돌발 퀴즈를 위한 가장 마지막 질문과 답변을 저장해 둠.
        userdb.insert_quiz(userid=user_id, type=100, query=query, response=response, answer="", info="")   
        # 이전 질문과 임베딩값 추가함.          
        res, prequery_docs, status = prequery_embed.delete_insert_doc(doc={'query':query, 'response':response},
                                                                    classification=prequery_embed_classification[user_mode])
        # 이전 답변 저장
        userdb.insert_assistants(user_id=user_id, preanswer=response)
        # 실패명 로그만 남기고 진행
        if status != 0:
            myutils.log_message(f'[call_chatting][error]==>insert_doc:{res}\n')
            
    else:
        if status == 1001: # time out일때
            query = "응답 시간 초과"
            response = "⚠️AI 응답이 없습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"
        else:
            query = "응답 에러"
            response = "⚠️AI 에러가 발생하였습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"

        error = f'generate_text_xxx fail=>model:{gpt_model}'
        myutils.log_message(f'[call_chatting][error]==>call_callback:{error}=>{response}\n')

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    myutils.log_message(f"*답변: {response}")
    template = callback_template.template_chatting(query=query, response=response, elapsed_time=el_time)         

    # 유사한 질문이 있으면 추가
    #myutils.log_message(f"\t[call_callback]prequery_docs\n{prequery_docs}\n")
    callback_template.similar_query(prequery_docs=prequery_docs, template=template)

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_chatting][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    