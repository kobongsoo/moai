import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from utils import generate_text_GPT2, generate_text_davinci, quiz_parser

def call_quiz(settings:dict, data:dict, instance:dict):

    gpt_model:str = settings['GPT_MODEL']    
    system_prompt = settings['SYSTEM_PROMPT']
    
    callbackurl = data['callbackurl']
    prompt = data['prompt']
    query = data['query']
    user_id = data['user_id']
    user_mode = data['user_mode']
    prequery_embed_classification = data['pre_class'] # 회사본문검색 이전 답변 저장.(순서대로 회사검색, 웹문서검색, AI응답답변)

    userdb = instance['userdb']
    myutils = instance['myutils']
    prequery_embed = instance['prequery_embed']
    quiz_callback_template = instance['quiz_callback_template']
    id_manager = instance['id_manager']

    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_quiz][start]")
    
    start_time = time.time()

    # 프롬프트 구성
    input_prompt = prompt if prompt else query
                
    if gpt_model.startswith("gpt-"):             
        response, status = generate_text_GPT2(gpt_model=gpt_model, prompt=input_prompt, system_prompt=system_prompt, 
                                              assistants=[], stream=True, timeout=20) #timeout=20초면 2번 돌게 되므로 총 40초 대기함
    else:
        response, status = generate_text_davinci(gpt_model=gpt_model, prompt=input_prompt, stream=True, timeout=20)

    if status != 0:
        if status == 1001: # time out일때
            query = "응답 시간 초과"
            response = "⚠️AI 응답이 없습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"
        else:
            query = "응답 에러"
            response = "⚠️AI 에러가 발생하였습니다. 잠시 후 다시 질문해 주세요.\n(" + response + ")"
    
        error = f'generate_text_xxx fail=>model:{gpt_model}'
        myutils.log_message(f'[call_quiz][error]==>call_callback:{error}=>{response}\n')

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    myutils.log_message(f"*답변: {response}")
    
    quizzes = quiz_parser(input_text=response) # 내용을 파싱해서 db에 담음.
    create_quiz:bool = False
    quiz_num = 0
    if len(quizzes) > 0:
        userdb.delete_quiz(userid=user_id) # 모든 퀴즈 db 삭제
        for idx, quiz in enumerate(quizzes):
            if quiz['query'] and quiz['answer']: # 질문, 정답이 존재하는 경우에만 추가
                res = userdb.insert_quiz(type=idx+1, userid=user_id, query=quiz['query'], answer=quiz['answer'], info=quiz['info'])
                quiz_num += 1
                create_quiz = True

    if create_quiz == True:
        template = quiz_callback_template.quiz_start(quiz_num=quiz_num, el_time=el_time) # 퀴즈시작 템플릿
    else:
        quick:dict = {'label':'퀴즈다시만들기..', 'message':'?돌발퀴즈.'}
        template = quiz_callback_template.quiz_error(text = f"⚠️다음기회에..\n퀴즈를 만들지 못했습니다.", quick=quick)# 퀴즈 생성 실패 템플릿
           
    myutils.log_message(f"\n\t돌발퀴즈\n({el_time})Q:{query}\nA:\n{response}\n")         

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_quiz][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    
    