#----------------------------------------------------------------------
# GPT를 카카오톡과 연동 예제
# - 설치 :pip install fastapi[all]
# - python 업데이트(옵션) : conda install -c anaconda python=3.10 (3.10이상 필요)
# - 실행 : uvicorn model1:app --host=0.0.0.0 --port=9000 --limit-concurrency=200
# - POST 테스트 docs : IP/docs
# - 출처 : https://fastapi.tiangolo.com/ko/
# - elasticsearh는 7.17 설치해야 함. => pip install elasticsearch==7.17
#----------------------------------------------------------------------
import torch
import argparse
import time
import os
import platform
import pandas as pd
import numpy as np
import random
import asyncio
import threading
import httpx
import openai    
import uvicorn
import warnings

from os import sys
from typing import Union, Dict, List, Optional
from typing_extensions import Annotated
from fastapi import FastAPI, Query, Cookie, Form, Request, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse
from elasticsearch import Elasticsearch, helpers  # ES 관련

from utils import create_index, make_docs_df, get_sentences, quiz_parser
from utils import load_embed_model, async_embedding, index_data, async_es_embed_query, async_es_embed_delete
from utils import async_chat_search, remove_prequery, get_title_with_urllink, make_prompt
from utils import generate_text_GPT2, generate_text_davinci, Google_Vision
from utils import IdManager, NaverSearchAPI, GoogleSearchAPI, ES_Embed_Text, MyUtils, SqliteDB, WebScraping, KarloAPI

from callback import call_text_search, call_web_search, call_chatting, call_url_summarize, call_ocr, call_ocr_summarize, call_quiz, call_paint
from chatbot import chatbot_check, get_quiz_template, get_user_mode, get_prequery_search_template
from chatbot import chatbot_text_search, chatbot_web_search, chatbot_chatting, chatbot_url_summarize, chatbot_ocr, chatbot_ocr_summarize, chatbot_quiz, chatbot_paint

from kakao_template import Callback_Template, Quiz_Callback_Template

from googletrans import Translator

# os가 윈도우면 from eunjeon import Mecab 
if platform.system() == 'Windows':
    os.environ["OMP_NUM_THREADS"] = '1' # 윈도우 환경에서는 쓰레드 1개로 지정함

# FutureWarning 제거
warnings.simplefilter(action='ignore', category=FutureWarning) 

#---------------------------------------------------------------------
# 전역 변수들 선언
# 설정값 settings.yaml 파일 로딩
myutils = MyUtils(yam_file_path='./data/settings.yaml')
settings = myutils.get_options()
assert len(settings) > 2, f'load settings error!!=>len(settigs):{len(settings)}'

print(f'='*80)
print(f'*ElasticSearch:{settings["ES_URL"]}')
print(f'\t- 본문검색 Index:{settings["ES_INDEX_NAME"]}')
print(f'\t- 이전질문 Index:{settings["ES_PREQUERY_INDEX_NAME"]}')
print(f'*BERT:{settings["E_MODEL_PATH"]}')
print(f'*GPT:{settings["GPT_MODEL"]}')

myutils.seed_everything()  # seed 설정
DEVICE = settings['GPU']
if DEVICE == 'auto':
    DEVICE = myutils.GPU_info() # GPU 혹은 CPU

print(f'*DEVICE: {DEVICE}')
#---------------------------------------------------------------------------
# 임베딩 모델 로딩
_, g_BI_ENCODER = load_embed_model(settings['E_MODEL_PATH'], settings['E_POLLING_MODE'], settings['E_OUT_DIMENSION'], DEVICE)
      
# GPT 모델 - GPT 3.5 Turbo 지정 : => 모델 목록은 : https://platform.openai.com/docs/models/gpt-4 참조                                                
openai.api_key = settings['GPT_TOKEN']# **GPT  key 지정
gpt_model = settings['GPT_MODEL']  #"gpt-4"#"gpt-3.5-turbo" #gpt-4-0314
#---------------------------------------------------------------------------
# 클래스 초기화
# db 관련
id_manager = IdManager()    # chabot3함수에서 중복 질문 방지를 위한 id 관리 클래스 초기화
userdb = SqliteDB(dbname='./data/kakao.db', assistants_len=settings['CHATTING_ASSISTANCE_LEN']) # SQLite DB 
print(f'*SQLite: ./data/kakao.db')

# 검색 관련
naver_api = NaverSearchAPI(client_id=settings['NAVER_CLIENT_ID'], client_secret=settings['NAVER_CLINET_SECRET']) # 네이버 검색 클래스 초기화
google_api = GoogleSearchAPI(api_key=settings['GOOGLE_API_KEY'], search_engine_id=settings['GOOGLE_SEARCH_ENGINE_ID']) # 구글 검색 클래스 초기화

# es 임베딩 관련
# 회사본문검색 이전 답변 저장.(순서대로 회사검색, 웹문서검색, AI응답답변)
index_name = settings['ES_PREQUERY_INDEX_NAME']
prequery_embed_class = ["company", "web", "ai"]  
prequery_embed = ES_Embed_Text(es_url=settings['ES_URL'], index_name=index_name, mapping=myutils.get_mapping_esindex(), bi_encoder=g_BI_ENCODER, float_type=settings["E_FLOAT_TYPE"], uid_min_score=0.10) # 임베딩 생성
    
# url 웹스크래핑
SCRAPING_WEB_MAX_LEN = settings['SCRAPING_WEB_MAX_LEN']  # 웹 url 스크래핑 할때 최대 길이  (webscraping 에서 최대값은 6000 이므로 6000보다 작게 설정해야함)
webscraping = WebScraping(scraping_web_max_len=SCRAPING_WEB_MAX_LEN)
    
# 이미지 OCR
# google_vision 인증 json 파일 => # 출처: https://yunwoong.tistory.com/148
service_account_jsonfile_path = "./data/vison-ocr.json"
google_vision = Google_Vision(service_account_jsonfile_path=service_account_jsonfile_path)
print(f'*google_vision: {service_account_jsonfile_path}')

# 콜백 템플릿
callback_template = Callback_Template(api_server_url=settings['API_SERVER_URL'], es_index_name=settings['ES_INDEX_NAME'], qmethod=settings['ES_Q_METHOD'], search_size=settings['ES_SEARCH_DOC_NUM'])
quiz_callback_template = Quiz_Callback_Template() # 퀴즈콜백템플릿

# 번역 
translator = Translator()

# Karlo (이미지생성)
kakako_rest_api_key = settings['KAKAO_REST_API_KEY']
karlo = KarloAPI(rest_api_key=kakako_rest_api_key)

# global 인스턴스 dict로 정의
global_instance:dict = {'myutils': myutils, 'id_manager': id_manager, 'userdb': userdb, 'naver_api': naver_api, 'google_api': google_api, 
                        'webscraping': webscraping, 'google_vision': google_vision, 'prequery_embed': prequery_embed,
                        'callback_template': callback_template, 'quiz_callback_template': quiz_callback_template, 
                        'translator': translator, 'karlo': karlo}

print(f'='*80)
#---------------------------------------------------------------------------

# http://10.10.4.10:9002/docs=>swagger UI, http://10.10.4.10:9000/redoc=>ReDoc UI 각각 비활성화 하려면
# => docs_url=None, redoc_url=None 하면 된다.
#app = FastAPI(redoc_url=None) #FastAPI 인스턴스 생성(*redoc UI 비활성화)
app = FastAPI()
templates = Jinja2Templates(directory="template_files") # html 파일이 있는 경로를 지정.
#----------------------------------------------------------------------
@app.get("/")
async def root():
    settings = myutils.get_options()
    return { "MoI(모아이)":"모아이(MoAI)", "1.임베딩모델": settings["E_MODEL_PATH"], "2.LLM모델": settings["GPT_MODEL"], "3.ES" : settings["ES_URL"], 
            "4.후보검색(1=함,0=안함)" : settings["ES_UID_SEARCH"], "5.검색방식(0=벡터다수일때 최대값, 1=벡터다수일때 평균, 2=벡터1개일때)" : settings["ES_Q_METHOD"]}
#----------------------------------------------------------------------
# GET : es/{인덱스명}/docs 검색(비동기)
# => http://127.0.0.1:9000/es/{인덱스}/docs?query=쿼리문장&search_size=5
# - in : query=쿼리할 문장, search_size=검색계수(몇개까지 검색 출력 할지)
# - out: 검색 결과(스코어, rfile_name, rfile_text)
#----------------------------------------------------------------------
@app.get("/es/{esindex}/docs")
async def search_documents(esindex:str, 
                     query: str = Query(..., min_length=1),  # ... 는 필수 입력 이고,min_length=1은 최소값이 1임.작으면 422 Unprocessable Entity 응답반환됨
                     search_size: int = Query(..., gt=0),    # ... 는 필수 입력 이고,gt=0은 0보다 커야 한다. 작으면 422 Unprocessable Entity 응답반환됨
                     qmethod: int=2,                         # option: qmethod=0 혹은 1(0=max벡터 구하기, 1=평균벡터 구하기 (default=0))혹은 2
                     show: int=1                             # 0=dict 형태로 보여줌, 1=txt 형태로 보여줌.
                     ):                          
                    
    error:str = 'success'
    query = query.strip()
    myutils.log_message(f'\n[info] get /es/{esindex}/docs start-----\nquery:{query}, search_size:{search_size}')

    settings = myutils.get_options()
    min_score = settings['ES_SEARCH_MIN_SCORE']
    
    try:
        # es로 임베딩 쿼리 실행      
        error, docs = await async_es_embed_query(settings=settings, esindex=esindex, query=query, 
                                                 search_size=search_size,bi_encoder=g_BI_ENCODER, qmethod=qmethod)
    except Exception as e:
        error = f'async_es_embed_query fail'
        msg = f'{error}=>{e}'
        myutils.log_message(f'[error] get /es/{esindex}/docs {msg}')
        raise HTTPException(status_code=404, detail=msg, headers={"X-Error": error},)
    
    if error != 'success':
        raise HTTPException(status_code=404, detail=error, headers={"X-Error": error},)
       
    context:str = ''
    response:dict = {}
    
    # show ==0 : dict 형태로 출력
    if show == 0:
        response = {"query":query, "docs": docs}
        return response
    else:
        for doc in docs:
            score = doc['score']
            if score > min_score:
                rfile_text = doc['rfile_text']
                if rfile_text:
                    formatted_score = "{:.2f}".format(score)
                    rfile_text = rfile_text.replace("\n", "<br>")
                    context += '<br>'+ rfile_text + '<br>[score:'+str(formatted_score)+']' + '<br>'  # 내용과 socore 출력
           
        #response = {"query":query, "docs": context}
        # HTML 문서 생성
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <title>내용보기</title>
        </head>
        <body>
            <p>Q: {query}<br>{context}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

#----------------------------------------------------------------------
# POST : es/{인덱스명}/docs/uids => uid 목록에 대한 검색(비동기)
# => http://127.0.0.1:9000/es/{인덱스}/docs/uid?query=쿼리문장&search_size=5
# - in : query=쿼리할 문장, search_size=검색계수(몇개까지 검색 출력 할지)
# - in(data) : DocsUidsIn=검색할 uid 목록
# - out: 검색 결과(스코어, rfile_name, rfile_text)
#----------------------------------------------------------------------

class DocsUidsIn(BaseModel):
    uids: list       # uid(문서 고유id)->rfilename
    
@app.post("/es/{esindex}/docs/uids")
async def search_documents_uid(esindex:str, 
                     Data:DocsUidsIn,
                     query: str = Query(..., min_length=1),     # ... 는 필수 입력 이고, min_length=1은 최소값이 1임. 작으면 422 Unprocessable Entity 응답반환됨
                     search_size: int = Query(..., gt=0),       # ... 는 필수 입력 이고, gt=0은 0보다 커야 한다. 작으면 422 Unprocessable Entity 응답반환됨
                     qmethod: int=2,                            # option: qmethod=0 혹은 1(0=max벡터 구하기, 1=평균벡터 구하기 (default=0))
                     ):    
    
    error:str = 'success'
    docs = []
    query = query.strip()
    uids = Data.uids 
    myutils.log_message(f'\n[info] post /es/{esindex}/docs/uids start-----\nquery:{query}, search_size:{search_size}, len(uids):{len(uids)}')

    settings = myutils.get_options()

    try:
        # es로 임베딩 쿼리 실행
        error, docs = await async_es_embed_query(settings=settings, esindex=esindex, query=query, 
                                                 search_size=search_size, bi_encoder=g_BI_ENCODER, qmethod=qmethod, 
                                                 uids=uids)
    except Exception as e:
        error = f'async_es_embed_query fail'
        msg = f'{error}=>{e}'
        myutils.log_message(f'[error] get /es/{esindex}/docs {msg}')
        raise HTTPException(status_code=404, detail=msg, headers={"X-Error": error},)
    
    if error != 'success':
        raise HTTPException(status_code=404, detail=error, headers={"X-Error": error},)
            
    return {"query":query, "docs": docs}
#----------------------------------------------------------------------
# 카카오 쳇봇 연동 콜백 함수
# - 콜백함수 정의 : 카카오톡은 응답시간이 5초로 제한되어 있어서, 
#   5초이상 응답이 필요한 경우(LLM 응답은 10~20초) AI 챗봇 설정-콜백API 사용 신청하고 연동해야한다. 
#----------------------------------------------------------------------
async def call_callback(settings:dict, data:dict):
    async with httpx.AsyncClient() as client: 
        
        await asyncio.sleep(1)

        user_id:str = data['user_id']
        user_mode:int = data['user_mode']
        callbackurl:str = data['callbackurl']
        
        assert settings, f'Error:settings is empty'
        assert user_id, f'Error:user_id is empty'
        assert callbackurl, f'Error:callbackurl is empty'

        #-------------------------------------------------------------------
        if user_mode == 0 or user_mode == 22 or user_mode == 23:  # RAS 검색
            template = call_text_search(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 1: # 웹검색
            template = call_web_search(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 2: # 채팅
            template = call_chatting(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 3: # 이미지 생성
            template = call_paint(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------      
        elif user_mode == 5: # URL 요약
            template = call_url_summarize(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 6: # 이미지 ocr
            template = call_ocr(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 7: # 이미지 ocr 요약인 경우
            template = call_ocr_summarize(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 8: # 도발퀴즈인 경우
            template = call_quiz(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        
        for i in range(3):
            # 콜백 url로 anwer 값 전송
            callback_response = await client.post(
                callbackurl,
                json=template
            )
                
            if callback_response.status_code == 200:
                myutils.log_message(f"\t[call_callback]callback 호출 성공\ncallbackurl:{callbackurl}\n")
                break
            else:  # 실패면 1초 대기했다가 다시 전송해봄
                myutils.log_message(f"\t[call_callback][error]callback 호출 실패(count:{i}): {callback_response.status_code}\ncallbackurl:{callbackurl}\n")
                await asyncio.sleep(1)
                continue

        myutils.log_message(f"=" * 80)
        return callback_response

#----------------------------------------------------------------------
# 테스트용
# => 회사규정문서 테스트용 
#----------------------------------------------------------------------                
@app.post("/test")
async def chabot_test(kakaoDict: Dict):

    result:dict = {};  query_format:str = ""; ocr_url:str = ""
    
    #await asyncio.sleep(1)
    kakao_userRequest = kakaoDict["userRequest"]  
    query:str = kakao_userRequest["utterance"]  # 질문
    callbackurl:str = kakao_userRequest["callbackUrl"] # callbackurl
    user_id:str = kakao_userRequest["user"]["id"]

    # 쿼리가 이미지인지 파악하기 위해 type을 얻어옴.'params': {'surface': 'Kakaotalk.plusfriend', 'media': {'type': 'image', 'url':'https://xxxx'}...}
    if 'media' in kakao_userRequest['params'] and 'type' in kakao_userRequest['params']['media']:
        query_format = kakao_userRequest['params']['media']['type']
        
    settings = myutils.get_options()
    #----------------------------------------
    # 체크해봄.
    check_res = chatbot_check(kakaoDict=kakaoDict, instance=global_instance)
    if check_res['error'] != 0:
        if len(check_res['template']) > 0:
            return JSONResponse(content=check_res['template'])
        return
    #----------------------------------------
    # quiz 처리
    quiz_dict:dict = {'userid': user_id, 'query': query}
    quiz_res = get_quiz_template(quiz_dict=quiz_dict, instance=global_instance)
    if len(quiz_res['template']) > 0:
        id_manager.remove_id_all(user_id) # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
        return JSONResponse(content=quiz_res['template'])                 
    #----------------------------------------
    # usermode 얻어옴.
    usermode_dict = {'userid': user_id, 'query': query, 'query_format': query_format}
    user_mode = get_user_mode(usermode_dict=usermode_dict, instance=global_instance)
    #----------------------------------------
    
    # 설정 값 얻어옴
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site, prequery 등을 얻어옴
    s_site:str = "naver" # 웹검색 사이트 기본은 네이버 
    e_prequery:int = 1  # 예전 유사질문 검색 (기본은 허용)
    llm_model:int = 0   # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    
    if setting != -1:
        s_site = setting.get('site', s_site)
        e_prequery = setting.get('prequery', e_prequery)

    # [bong][2024-04-18] settings.yaml에 DISABLE_SEARCH_PREANSWER=1 설정되어 있으면 이전검색 무조건 안함.
    if settings['DISABLE_SEARCH_PREANSWER'] == 1:
        e_prequery:int = 0
    
    e_prequery:int = 0  # 예전 유사질문 검색 (*테스트를 위해서 무조건 유사질문 검색 하지 않도록 막아놈=0으로 설정.)

    # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    llm_model = setting.get('llmmodel', llm_model)
    #-------------------------------------
    # 이전 질문 검색 처리.
    prequery_dict:dict = {'userid': user_id, 'query': query, 'usermode':user_mode, 'pre_class': prequery_embed_class, 'set_prequery': e_prequery}
    pre_template = get_prequery_search_template(prequery_dict=prequery_dict, instance=global_instance)
    if pre_template: # 이전질문 있으면 이전 질문을 보여줌.
        id_manager.remove_id_all(user_id) # id 제거
        return JSONResponse(content=pre_template)   
    #-------------------------------------    
    # 출력 dict (docs = 본문검색(0), s_best_contexts = 웹검색(1))
    result:dict = {'error':0, 'query':'', 'prompt': '', 'template': '', 'docs':[],  's_best_contexts': [] } 
    #--------------------------------------
    # 0=회사규정 RAG(수정된 인덱싱 데이터)
    if user_mode == 0:
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER}
        chatbot_text_search(settings=settings, data=text_search_dict, instance=global_instance, result=result)
        # 1002=질문에 맞는 내용을 찾지 못한 경우 '질문에 맞는 내용을 찾지 못했습니다. 질문을 다르게 해 보세요.' 메시지만 띄워줌.(콜백호출안함)
        if result['error'] == 1002:
            json_response = JSONResponse(content=result['template'])
            id_manager.remove_id_all(user_id) # id 제거
            return json_response 
        elif result['error'] != 0:
            return
    #--------------------------------------
     # 22=회사규정 RAG(원본 인덱싱 데이터)
    if user_mode == 22 or user_mode == 23:
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER}
        es_index_name:str = ""
        if user_mode == 22:
            # *ES_INDEX_NAME_2를 설정함
            es_index_name = settings['ES_INDEX_NAME_2']
        else:
            # *ES_INDEX_NAME_3를 설정함
            es_index_name = settings['ES_INDEX_NAME_3']

        #myutils.log_message(f"\t[chabot_test]user_mode:{user_mode}, es_inde_name:{es_index_name}\n")
        chatbot_text_search(settings=settings, data=text_search_dict, instance=global_instance, result=result, es_index_name=es_index_name)
        # 1002=질문에 맞는 내용을 찾지 못한 경우 '질문에 맞는 내용을 찾지 못했습니다. 질문을 다르게 해 보세요.' 메시지만 띄워줌.(콜백호출안함)
        if result['error'] == 1002:
            json_response = JSONResponse(content=result['template'])
            id_manager.remove_id_all(user_id) # id 제거
            return json_response 
        elif result['error'] != 0:
            return
    #--------------------------------------
    call:bool = False
    for i in range(3):
        json_response = JSONResponse(content=result['template'])
        if json_response.status_code == 200:
            
            data:dict = {'callbackurl':callbackurl, 'user_mode':user_mode, 'user_id': user_id, 'pre_class': prequery_embed_class,
                         'prompt': result['prompt'], 'query':result['query'], 'docs':result['docs'], 
                         's_best_contexts': result['s_best_contexts'], 'llm_model': llm_model}

            #myutils.log_message(f"\t[chabot_test]data:{data}\n")
            
            # 비동기 작업을 스케줄링 콜백 호출
            task = asyncio.create_task(call_callback(settings=settings, data=data))
            
            myutils.log_message(f"\t[chabot]==>성공: status_code:{json_response.status_code}\ncallbackurl: {callbackurl}\n")  
            call = True
            break
        else:
            myutils.log_message(f"\t[chabot]==>실패(count:{i}): status_code:{json_response.status_code}\ncallbackurl: {callbackurl}\n")    
            continue
    
    if call == False:
        id_manager.remove_id_all(user_id) # id 제거
   
    return json_response
#--------------------------------------------------------------------
    
#----------------------------------------------------------------------
# 모아이 챗봇
#----------------------------------------------------------------------                
@app.post("/chatbot3")
async def chabot(kakaoDict: Dict):

    result:dict = {};  query_format:str = ""; ocr_url:str = ""
    
    #await asyncio.sleep(1)
    kakao_userRequest = kakaoDict["userRequest"]  
    query:str = kakao_userRequest["utterance"]  # 질문
    callbackurl:str = kakao_userRequest["callbackUrl"] # callbackurl
    user_id:str = kakao_userRequest["user"]["id"]

    # 쿼리가 이미지인지 파악하기 위해 type을 얻어옴.'params': {'surface': 'Kakaotalk.plusfriend', 'media': {'type': 'image', 'url':'https://xxxx'}...}
    if 'media' in kakao_userRequest['params'] and 'type' in kakao_userRequest['params']['media']:
        query_format = kakao_userRequest['params']['media']['type']
        
    settings = myutils.get_options()
    #----------------------------------------
    # 체크해봄.
    check_res = chatbot_check(kakaoDict=kakaoDict, instance=global_instance)
    if check_res['error'] != 0:
        if len(check_res['template']) > 0:
            return JSONResponse(content=check_res['template'])
        return
    #----------------------------------------
    # quiz 처리
    quiz_dict:dict = {'userid': user_id, 'query': query}
    quiz_res = get_quiz_template(quiz_dict=quiz_dict, instance=global_instance)
    if len(quiz_res['template']) > 0:
        id_manager.remove_id_all(user_id) # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
        return JSONResponse(content=quiz_res['template'])                 
    #----------------------------------------
    # usermode 얻어옴.
    usermode_dict = {'userid': user_id, 'query': query, 'query_format': query_format}
    user_mode = get_user_mode(usermode_dict=usermode_dict, instance=global_instance)
    #----------------------------------------
    
    # 설정 값 얻어옴
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site, prequery 등을 얻어옴
    s_site:str = "naver" # 웹검색 사이트 기본은 네이버 
    e_prequery:int = 1  # 예전 유사질문 검색 (기본은 허용)
    if setting != -1:
        s_site = setting.get('site', s_site)
        e_prequery = setting.get('prequery', e_prequery)

    # [bong][2024-04-18] settings.yaml에 DISABLE_SEARCH_PREANSWER=1 설정되어 있으면 이전검색 무조건 안함.
    if settings['DISABLE_SEARCH_PREANSWER'] == 1:
        e_prequery:int = 0

    # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    llm_model:int = 0   # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    llm_model = setting.get('llmmodel', llm_model)
    #-------------------------------------
    # 이전 질문 검색 처리.
    prequery_dict:dict = {'userid': user_id, 'query': query, 'usermode':user_mode, 'pre_class': prequery_embed_class, 'set_prequery': e_prequery}
    pre_template = get_prequery_search_template(prequery_dict=prequery_dict, instance=global_instance)
    if pre_template: # 이전질문 있으면 이전 질문을 보여줌.
        id_manager.remove_id_all(user_id) # id 제거
        return JSONResponse(content=pre_template)   
    #-------------------------------------    
    # 출력 dict (docs = 본문검색(0), s_best_contexts = 웹검색(1))
    result:dict = {'error':0, 'query':'', 'prompt': '', 'template': '', 'docs':[],  's_best_contexts': [] } 
    #--------------------------------------
    # 0=본문검색(인덱싱 데이터)
    if user_mode == 0:
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER}
        chatbot_text_search(settings=settings, data=text_search_dict, instance=global_instance, result=result)
        # 1002=질문에 맞는 내용을 찾지 못한 경우 '질문에 맞는 내용을 찾지 못했습니다. 질문을 다르게 해 보세요.' 메시지만 띄워줌.(콜백호출안함)
        if result['error'] == 1002:
            json_response = JSONResponse(content=result['template'])
            id_manager.remove_id_all(user_id) # id 제거
            return json_response 
        elif result['error'] != 0:
            return
    #--------------------------------------
    # 1=웹검색
    if user_mode == 1:
        web_search_dict:dict = {'userid': user_id, 'query': query, 'search_site': s_site, }
        chatbot_web_search(settings=settings, data=web_search_dict, instance=global_instance, result=result)
    #--------------------------------------
    # 2=채팅
    if user_mode == 2:
        chatting_dict:dict = {'userid': user_id, 'query': query}
        chatbot_chatting(settings=settings, data=chatting_dict, instance=global_instance, result=result)
    #--------------------------------------
    # 3=이미지 생성
    if user_mode == 3:
        paint_dict:dict = {'userid': user_id, 'query': query}
        chatbot_paint(settings=settings, data=paint_dict, instance=global_instance, result=result)
    #--------------------------------------    
    # 5=URL 요약
    if user_mode == 5:
        url_summarize_dict:dict = {'userid': user_id, 'query': query}
        chatbot_url_summarize(settings=settings, data=url_summarize_dict, instance=global_instance, result=result)
    #--------------------------------------
    # 6=이미지 OCR
    if user_mode == 6:
        ocr_dict:dict = {'userid': user_id, 'query': query, 'userRequest': kakaoDict["userRequest"]}
        chatbot_ocr(settings=settings, data=ocr_dict, instance=global_instance, result=result)
    #--------------------------------------  
    # 7=이미지 OCR 내용 요약
    if user_mode == 7:
        ocr_summarize_dict:dict = {'userid': user_id, 'query': query}
        chatbot_ocr_summarize(settings=settings, data=ocr_summarize_dict, instance=global_instance, result=result)
    #-------------------------------------- 
    # 8=돌발퀴즈?
    if user_mode == 8:
        quiz_dict:dict = {'userid': user_id, 'query': query, 'quiz_res': quiz_res['quiz']}
        chatbot_quiz(settings=settings, data=quiz_dict, instance=global_instance, result=result)
    #-------------------------------------- 
    
    call:bool = False
    for i in range(3):
        json_response = JSONResponse(content=result['template'])
        if json_response.status_code == 200:
            
            data:dict = {'callbackurl':callbackurl, 'user_mode':user_mode, 'user_id': user_id, 'pre_class': prequery_embed_class,
                         'prompt': result['prompt'], 'query':result['query'], 'docs':result['docs'], 
                         's_best_contexts': result['s_best_contexts'], 'llm_model': llm_model}
            
            # 비동기 작업을 스케줄링 콜백 호출
            task = asyncio.create_task(call_callback(settings=settings, data=data))
            
            myutils.log_message(f"\t[chabot]==>성공: status_code:{json_response.status_code}\ncallbackurl: {callbackurl}\n")  
            call = True
            break
        else:
            myutils.log_message(f"\t[chabot]==>실패(count:{i}): status_code:{json_response.status_code}\ncallbackurl: {callbackurl}\n")    
            continue
    
    if call == False:
        id_manager.remove_id_all(user_id) # id 제거
   
    return json_response
#--------------------------------------------------------------------
    
def set_userinfo(content, user_mode:int):
    myutils.log_message(f't\[searchdoc]==>content:{content}\n')
    user_id:str = content["user"]["id"]
    if user_id.strip()=="":
        return 1001
    
    # id_manager 에 id가 존재하면 '이전 질문 처리중'이므로, return 시킴
    # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 해당 user_id 가 있는지 검색
    if id_manager.check_id_exists(user_id):
        myutils.log_message(f't\[searchdoc]==>이전 질문 처리중:{user_id}\n')
        return 1002

    userdb.insert_user_mode(user_id, user_mode) # 해당 사용자의 user_id 모드를 0로 업데이트
    userdb.delete_assistants(user_id=user_id)   # 이전 질문 내용 모두 제거
    userdb.delete_quiz_all(userid=user_id)      # 모든 퀴즈 db 삭제

    return 0
 
#-----------------------------------------------------------
# 본문검색
@app.post("/searchdoc")
async def searchdoc(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=0) != 0:
        return

    template = callback_template.searchdoc()
    json_response = JSONResponse(content=template)
    return json_response

#-----------------------------------------------------------
# 회사문서검색
@app.post("/searchdoc2")
async def searchdoc(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=22) != 0:
        return

    template = callback_template.searchdoc()
    json_response = JSONResponse(content=template)
    return json_response
    
#----------------------------------------------------------------------
# 회사문서검색
@app.post("/searchdoc3")
async def searchdoc(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=23) != 0:
        return

    template = callback_template.searchdoc()
    json_response = JSONResponse(content=template)
    return json_response
#----------------------------------------------------------------------
# 웹검색
@app.post("/searchweb")
async def searchweb(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=1) != 0:
        return
    
    template = callback_template.searchweb()
    json_response = JSONResponse(content=template)
    return json_response

#----------------------------------------------------------------------
# 채팅하기
@app.post("/searchai")
async def chatting(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=2) != 0:
        return
       
    template = callback_template.chatting()
    json_response = JSONResponse(content=template)    
    return json_response
#----------------------------------------------------------------------
# 이미지생성 클릭릭
@app.post("/paint")
async def painting(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=3) != 0:
        return
       
    template = callback_template.paint()
    json_response = JSONResponse(content=template)    
    return json_response
#----------------------------------------------------------------------  

# setting 관련
@app.post("/setting/save")
async def setting_save(request: Request): 
    form = await request.form()
    user_id = form.get("user_id")
    search_site = form.get("search_engine")
    pre_query = form.get("prequery")
    llm_model = form.get("llm_model2") # [bong][2024-04-18] 웹에서 설정한 llm_model 종류 읽어옴
        
    # 변경값으로 셋팅.
    # 해당 사용자의 user_id site를 업데이트
    error = userdb.insert_setting(user_id=user_id, site=search_site, prequery=int(pre_query), llmmodel=int(llm_model)) 
    setting_success:bool = False
    if error == 0:
        setting_success = True
    else:
        myutils.log_message(f"\t[setting]==>setting_save fail!\n")
        
    return templates.TemplateResponse("setting.html", {"request": request, "user_id":user_id, "search_site": search_site, 
                                                       "pre_query": int(pre_query), "llm_model": int(llm_model), 
                                                       "setting_success": setting_success })
#----------------------------------------------------------------------    
# setting.html 로딩    
@app.get("/setting/form")
async def setting_form(request:Request, user_id:str):
    assert user_id, f'user_id is empty'
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site를 얻어옴
    
    search_site:str = "naver" # 웹검색 사이트 (기본은 naver)
    pre_query:int=1   # 예전 유사 질문 검색(기본=1(검색함))
    llm_model:int=0   # [bong][2024-04-18] llm 모델 (0=gpt, 1=gamma(구글))
    if setting != -1 and setting['site']:
        search_site = setting['site']
        pre_query = setting['prequery']
        llm_model = setting['llmmodel']
        
    #myutils.log_message(f"\t[setting]==>setting_form=>user_id:{user_id}, search_site:{search_site}, prequery:{pre_query}\n")
    
    return templates.TemplateResponse("setting.html", {"request": request, "user_id":user_id, 
                                                       "search_site": search_site, "pre_query":pre_query, "llm_model":llm_model})
#----------------------------------------------------------------------
@app.post("/setting")
async def setting(content: Dict):
    user_id:str = content["userRequest"]["user"]["id"]
    assert user_id, f'user_id is empty'
    
    api_server_url:str = settings['API_SERVER_URL']
    
    search_site:str = "naver" # 웹검색 사이트 (기본은 naver)
    pre_query:int=1   # 예전 유사 질문 검색(기본=1(검색함))
    llm_model:int=0   # llm 모델 종류(0=gpt, 1=gemma)
    llm_model_list:list = ['GPT','구글 Gemma']   
    pre_query_str:str = '검색함'
    user_mode_list:list = ['회사문서검색(수동)','웹검색(1)','채팅하기(2)', '이미지생성(3)']   
    user_mode_str:str = "없음"
    llm_model_str:str = ""
    
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site를 얻어옴
    #myutils.log_message(f"\t[setting]==>setting:{setting}\n")
    
    user_mode=userdb.select_user_mode(user_id=user_id)
    if user_mode == -1:
        user_mode = 0

    if user_mode == 22:
        user_mode_str = '회사문서검색(원본)'
    elif user_mode == 23:
        user_mode_str = '회사문서검색(GPT)'
    else:
        user_mode_str = user_mode_list[user_mode]
    
    if setting != -1 and setting['site']:
        search_site = setting['site']
        pre_query = setting['prequery']
        llm_model = setting['llmmodel']
     
    if pre_query != 1:
        pre_query_str:str = '검색안함'

    # [bong][2024-04-18] llm 모델명 설명
    if llm_model > 1:
        llm_model = 0
    llm_model_str = llm_model_list[llm_model]
        
    linkurl = f'{api_server_url}/setting/form?user_id={user_id}'
    descript = f'🧒 사용자ID: {user_id}\n\n🕹 현재 동작모드: {user_mode_str}\n💬 에전유사 질문검색: {pre_query_str}\n🌐 웹검색 사이트: {search_site}\n😀AI 모델: {llm_model_str}\n\n예전유사 질문검색, 웹검색 사이트, AI 모델등이 변경을 원하시면 설정하기를 눌러 변경해 주세요.'
    
    template = callback_template.setting(linkurl=linkurl, descript=descript)    
    json_response = JSONResponse(content=template)
    return json_response
#----------------------------------------------------------------------

#============================================================
def main():
    # 메인 함수의 코드를 여기에 작성합니다.
    return
   
if __name__ == "__main__":
    # 스크립트가 직접 실행될 때만 main 함수를 호출합니다.
    main()
#============================================================