import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from utils import generate_text_GPT2, generate_text_davinci, generate_Gemma, generate_Gemini_multi

def call_chatting(settings:dict, data:dict, instance:dict):
    
    gpt_model:str = settings['GPT_MODEL']    
    system_prompt = settings['SYSTEM_PROMPT']

    max_tokens = settings.get('GPT_MAX_TOKENS', 1024)
    temperature = settings.get('GPT_TEMPERATURE', 1.0)
    top_p = settings.get('GPT_TOP_P', 0.1)
    stream = settings.get('GTP_STREAM', False)

    # [bong][2024-04-26] Gemini 모델 사용을 위한 설정값 
    gemini_model_name = settings['GEMINI_MODEL_NAME']
    google_api_key = settings['GOOGLE_API_KEY']
    
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

    # [bong][2024-04-18] llm 모델 종류 스트링 설정(0=GPT, 1=구글 Gemma, 2=구글 gemini)
    llm_model = data['llm_model']  
    llm_model_str:str = gpt_model
    if llm_model == 2:
        llm_model_str:str = gemini_model_name
    elif llm_model == 1:
        llm_model_str:str = hf_model_name
        
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

    if llm_model == 2: # [bong][2024-04-26] llm 모델 종류 2 = 구글 gemini 호출
        prequerys:list = []
        preanswers:list = []
        
        res = userdb.select_assistants(user_id=user_id)
        if res != -1:
            for res1 in res:
                prequerys.append(res1['prequery'])
                preanswers.append(res1['preanswer'])

        response, status = generate_Gemini_multi(model_name=gemini_model_name, 
                                                 prompt=input_prompt, 
                                                 google_api_key=google_api_key,
                                                 prequerys=prequerys, 
                                                 preanswers=preanswers)
        
    elif llm_model == 1: # [bong][2024-04-18] llm 모델 종류 1= 구글 gemma 호출
        response, status = generate_Gemma(hf_model_name=hf_model_name, 
                                          prompt=input_prompt, 
                                          max_tokens=gemma_max_tokens,
                                          hf_auth_key=hf_auth_key)
    else:
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
    prequery_docs_embed:list = []
    if status == 0:
        # 돌발 퀴즈를 위한 가장 마지막 질문과 답변을 저장해 둠.
        userdb.insert_quiz(userid=user_id, type=100, query=query, response=response, answer="", info="")   
        # 이전 질문과 임베딩값 추가함.          
        res, prequery_docs_embed, status = prequery_embed.delete_insert_doc(doc={'query':query, 'response':response},
                                                                    classification=prequery_embed_classification[user_mode])
        # [bong][2024-04-26] 질문 저장 추가됨 => 이전 질문과 답변 저장해둠.
        userdb.insert_assistants(user_id=user_id, prequery=input_prompt, preanswer=response)
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
    # [bong][2024-04-18] llm 모델 종류 표기(0=GPT, 1=구글 Gemma)
    response = f"*AI모델:{llm_model_str}\n\n"+response
    template = callback_template.template_chatting(query=query, response=response, elapsed_time=el_time)         

    # 유사한 질문이 있으면 추가
    #myutils.log_message(f"\t[call_callback]prequery_docs_embed\n{prequery_docs_embed}\n")
    callback_template.similar_query(prequery_docs=prequery_docs_embed, template=template)

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_chatting][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    