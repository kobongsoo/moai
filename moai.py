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
import requests

from os import sys
from typing import Union, Dict, List, Optional
from typing_extensions import Annotated
from fastapi import FastAPI, Query, Cookie, Form, Request, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.responses import RedirectResponse
from elasticsearch import Elasticsearch, helpers  # ES 관련
from datetime import datetime

from utils import create_index, make_docs_df, get_sentences, quiz_parser
from utils import load_embed_model, async_embedding, index_data, async_es_embed_query, async_es_embed_delete
from utils import async_chat_search, remove_prequery, get_title_with_urllink, make_prompt
from utils import generate_text_GPT2, generate_text_davinci, Google_Vision
from utils import IdManager, NaverSearchAPI, GoogleSearchAPI, ES_Embed_Text, MyUtils, SqliteDB, WebScraping, KarloAPI

from callback import call_text_search, call_web_search, call_chatting, call_url_summarize, call_ocr, call_ocr_summarize, call_quiz, call_paint, call_userdoc_search, call_music, call_gpt_4o_vision
from chatbot import chatbot_check, get_quiz_template, get_user_mode, get_prequery_search_template
from chatbot import chatbot_text_search, chatbot_web_search, chatbot_chatting, chatbot_url_summarize, chatbot_ocr, chatbot_ocr_summarize, chatbot_quiz, chatbot_paint, chatbot_userdoc_search, chatbot_create_music, chatbot_check_create_music, chatbot_gpt_4o_vision_save_image, chatbot_get_music_limit

from kakao_template import Callback_Template, Quiz_Callback_Template

from googletrans import Translator

# [bong][2024-05-21] ReRank 설정
from rerank import ReRank

# [bong][2024-06-11] SUNO 설정
from music import SUNO

# [bong][2024-06-13] gpt-4o 설정
from vision import GPT_4O_VISION

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
print(f'*RERANK:{settings["RERANK_MODEL_PATH"]}')

myutils.seed_everything()  # seed 설정
DEVICE = settings['GPU']
if DEVICE == 'auto':
    DEVICE = myutils.GPU_info() # GPU 혹은 CPU
#---------------------------------------------------------------------------
# 임베딩 모델 로딩
_, g_BI_ENCODER = load_embed_model(settings['E_MODEL_PATH'], settings['E_POLLING_MODE'], settings['E_OUT_DIMENSION'], DEVICE)

# [bong][2024-05-21] ReRank 모델 설정
g_RERANK_MODEL = ReRank(model_path=settings['RERANK_MODEL_PATH'])

# GPT 모델 - GPT 3.5 Turbo 지정 : => 모델 목록은 : https://platform.openai.com/docs/models/gpt-4 참조                                                
openai.api_key = settings['GPT_TOKEN']# **GPT  key 지정
gpt_model = settings['GPT_MODEL']  #"gpt-4"#"gpt-3.5-turbo" #gpt-4-0314
#---------------------------------------------------------------------------
# 클래스 초기화
# db 관련
id_manager = IdManager()    # chabot3함수에서 중복 질문 방지를 위한 id 관리 클래스 초기화
userdb = SqliteDB(dbname='./data/kakao.db', assistants_len=settings['CHATTING_ASSISTANCE_LEN']) # SQLite DB 
print(f'*SQLite: ./data/kakao.db')

# 검색 관련kakao
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

# [bong][2024-06-11] SUNO 설정
suno = SUNO()

# [bong][2024-06-13] GPT-40-VISION 설정
gpt_4o_vision = GPT_4O_VISION(open_api_key=openai.api_key)

# global 인스턴스 dict로 정의
global_instance:dict = {'myutils': myutils, 'id_manager': id_manager, 'userdb': userdb, 'naver_api': naver_api, 'google_api': google_api, 
                        'webscraping': webscraping, 'google_vision': google_vision, 'prequery_embed': prequery_embed,
                        'callback_template': callback_template, 'quiz_callback_template': quiz_callback_template, 
                        'translator': translator, 'karlo': karlo, 'suno': suno, 'gpt_4o_vision': gpt_4o_vision}

print(f'='*80)
#---------------------------------------------------------------------------

# http://10.10.4.10:9002/docs=>swagger UI, http://10.10.4.10:9000/redoc=>ReDoc UI 각각 비활성화 하려면
# => docs_url=None, redoc_url=None 하면 된다.
#app = FastAPI(redoc_url=None) #FastAPI 인스턴스 생성(*redoc UI 비활성화)
app = FastAPI()
templates = Jinja2Templates(directory="template_files") # html 파일이 있는 경로를 지정.
#----------------------------------------------------------------------

#==============================================================
# [bong][2024-05-21] ReRank 사용일때 처리
#==============================================================

def rerank(rerank_model, query:str, docs:list):
    rerank_rfile_texts = [doc['rfile_text'] for doc in docs] # docs에서 rfile_text 만 뽑아내서 리스트 만듬
    rerank_rfile_names = [doc['rfile_name'] for doc in docs] # docs에서 rfile_name 만 뽑아내서 리스트 만듬

    # 스코어 구함.
    rerank_scores = rerank_model.compute_score(query=query, contexts=rerank_rfile_texts)

    # 세 리스트를 결합하여 하나의 리스트로 생성
    rerank_combined_list = list(zip(rerank_scores, rerank_rfile_texts, rerank_rfile_names))

    # scores 값을 기준으로 내림차순으로 정렬
    rerank_sorted_list = sorted(rerank_combined_list, key=lambda x: x[0], reverse=True)
            
    # 정렬된 리스트를 원하는 형식의 딕셔너리 리스트로 변환
    docs:list=[] # 초기화하고
    docs = [{'rfile_name': name, 'rfile_text': text, 'score': score} for score, text, name in rerank_sorted_list]

    #print(f'\n*[rerank] docs\n{docs}')
    
    return docs
#==============================================================    

@app.get("/")
async def root():
    settings = myutils.get_options()
    return { "MoI(모아이)":"모아이(MoAI)", "1.임베딩모델": settings["E_MODEL_PATH"], "2.LLM모델": settings["GPT_MODEL"], "3.ES" : settings["ES_URL"], 
            "4.BM25검색(0=안함/1=함+후보적용/2=함+RRF적용)" : settings["ES_UID_SEARCH"], "5.검색방식(0=벡터다수일때 최대값, 1=벡터다수일때 평균, 2=벡터1개일때)" : settings["ES_Q_METHOD"],
           "6.ReRank(0=안함/1=함)":settings["USE_RERANK"], "7.RERANK 모델":settings["RERANK_MODEL_PATH"], "8.검색최소스코어(유사도가 이하이면 검색내용제거)":settings["ES_SEARCH_MIN_SCORE"]}

#---------------------------------------------------------------------
# [bong][2024-06-04] 외부 url 호출후 리턴받은 값을 json으로 출력하는 예시
#---------------------------------------------------------------------
@app.get("/redirect")
async def redirect():
    url = "https://a54f-124-194-84-190.ngrok-free.app/search/query?user_id=bong9431&query=제주도관광지추천"
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"*result: {result}")
        print(f"*text: {result[0]}")
        print(f"*context: {result[1]}")
        print(f"*status: {result[2]}")
        print(f"*doc_names:{result[3]}")
        
        return JSONResponse(content=result)
    else:
        return JSONResponse(content={"error": "Failed to fetch data"}, status_code=response.status_code)
    
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
    use_rerank = settings['USE_RERANK'] # [bong][2024-05-21] ReRank 사용 유.무
    
    try:
        # es로 임베딩 쿼리 실행      
        error, docs = await async_es_embed_query(settings=settings, esindex=esindex, query=query, 
                                                 search_size=search_size,bi_encoder=g_BI_ENCODER, qmethod=qmethod)

        #==============================================================
        # [bong][2024-05-21] ReRank 사용일때 처리
        #==============================================================
        if use_rerank == 1:
            docs = rerank(rerank_model = g_RERANK_MODEL, query=query, docs=docs)
        #==============================================================

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
                    context += '=================================================================<br>[score: ' + str(formatted_score) + ']'+ '<br>' + rfile_text + '<br>'  # 내용과 socore 출력
           
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
        #==============================================================
        # [bong][2024-05-21] ReRank 사용일때 처리
        #==============================================================
        if use_rerank == 1:
            docs = rerank(rerank_model = g_RERANK_MODEL, query=query, docs=docs)
        #==============================================================
    
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
#   콜백API 도 최대 1분까지만 가능함.그 이상은 폴링방식으로 할수 밖에 없음.
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
        elif user_mode == 30: # [bong][2024-06-04] 개인문서검색
            template = call_userdoc_search(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 31: # [bong][2024-06-11] 음악생성(text)
            template = call_music(settings=settings, data=data, instance=global_instance)
        #-------------------------------------------------------------------
        elif user_mode == 32: # [bong][2024-06-13] 음악생성(이미지)
            template = call_gpt_4o_vision(settings=settings, data=data, instance=global_instance)

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

    result:dict = {};  query_format:str = ""; ocr_url:str = "";extra_id:str=""
    
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
        llm_model = setting.get('llmmodel', llm_model)  # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    
    # [bong][2024-04-18] settings.yaml에 DISABLE_SEARCH_PREANSWER=1 설정되어 있으면 이전검색 무조건 안함.
    if settings['DISABLE_SEARCH_PREANSWER'] == 1:
        e_prequery:int = 0
    
    #e_prequery:int = 0  # 예전 유사질문 검색 (*테스트를 위해서 무조건 유사질문 검색 하지 않도록 막아놈=0으로 설정.)

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
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER, 'rerank_model': g_RERANK_MODEL}
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
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER, 'rerank_model': g_RERANK_MODEL}
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
    # [bong][2024-06-04] 30=개인문서검색
    if user_mode == 30:
        userdocsearch:dict = {'userid': user_id, 'query': query}
        chatbot_userdoc_search(settings=settings, data=userdocsearch, instance=global_instance, result=result)
        # extra_id(별칭) 얻어옴.
        res = userdb.select_setting(user_id=user_id)
        if res != -1:
            extra_id = res['extraid']
    #-------------------------------------- 
    call:bool = False
    for i in range(3):
        json_response = JSONResponse(content=result['template'])
        if json_response.status_code == 200:
            
            data:dict = {'callbackurl':callbackurl, 'user_mode':user_mode, 'user_id': user_id, 'pre_class': prequery_embed_class,
                         'prompt': result['prompt'], 'query':result['query'], 'docs':result['docs'], 
                         's_best_contexts': result['s_best_contexts'], 'llm_model': llm_model, 'extra_id': extra_id}

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

    result:dict = {};  query_format:str = ""; ocr_url:str = ""; extra_id:str=""
    
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
    myutils.log_message(f't\[user_mode]==>{user_mode}\n')
    #----------------------------------------
    
    # 설정 값 얻어옴
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site, prequery 등을 얻어옴
    s_site:str = "naver" # 웹검색 사이트 기본은 네이버 
    e_prequery:int = 1  # 예전 유사질문 검색 (기본은 허용)
    llm_model:int = 0   # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)
    if setting != -1:
        s_site = setting.get('site', s_site)
        e_prequery = setting.get('prequery', e_prequery)
        llm_model = setting.get('llmmodel', llm_model)  # [bong][2024-04-18] llm 모델 종류(0=GPT, 1=구글 Gemma)

    # [bong][2024-04-18] settings.yaml에 DISABLE_SEARCH_PREANSWER=1 설정되어 있으면 이전검색 무조건 안함.
    if settings['DISABLE_SEARCH_PREANSWER'] == 1:
        e_prequery:int = 0
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
    # 0=회사규정검색색(인덱싱 데이터)
    if user_mode == 0:
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER, 'rerank_model': g_RERANK_MODEL}
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
    # 22=EZis-C Q&A
    if user_mode == 22 or user_mode == 23:
        text_search_dict:dict = {'userid': user_id, 'query': query, 'bi_encoder': g_BI_ENCODER, 'rerank_model': g_RERANK_MODEL}
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
    # [bong][2024-06-04] 30=개인문서검색
    if user_mode == 30:
        userdocsearch:dict = {'userid': user_id, 'query': query}
        chatbot_userdoc_search(settings=settings, data=userdocsearch, instance=global_instance, result=result)
        # extra_id(별칭) 얻어옴.
        res = userdb.select_setting(user_id=user_id)
        if res != -1:
            extra_id = res['extraid']
    #-------------------------------------- 
    # [bong][2024-06-11] 31=text로 음악생성, 
    if user_mode == 31:
        music:dict = {'userid': user_id, 'query': query}
        chatbot_create_music(settings=settings, data=music, instance=global_instance, result=result)
        json_response = JSONResponse(content=result['template'])
        id_manager.remove_id_all(user_id) # id 제거
        return json_response 

    # [bong][2024-06-11] 32=이미지로 음악생성
    # => URL 이미지 다운로드 => 사이즈변경후 로컬 저장
    if user_mode == 32:
        gpt_4o_vision_dict:dict = {'userid': user_id, 'query': query, 'userRequest': kakaoDict["userRequest"]}
        chatbot_gpt_4o_vision_save_image(settings=settings, data=gpt_4o_vision_dict, instance=global_instance, result=result)

    # [bong][2024-06-11] 33=^노래확인^ 인경우
    if user_mode == 33:
        music:dict = {'userid': user_id, 'query': query}
        chatbot_check_create_music(settings=settings, data=music, instance=global_instance, result=result)
        json_response = JSONResponse(content=result['template'])
        id_manager.remove_id_all(user_id) # id 제거
        return json_response 

    # [bong][2024-06-14] suno 남은계수 얻기
    if user_mode == 34:
        music:dict = {'userid': user_id, 'query': query}
        chatbot_get_music_limit(settings=settings, data=music, instance=global_instance, result=result)
        json_response = JSONResponse(content=result['template'])
        id_manager.remove_id_all(user_id) # id 제거
        return json_response 
    #-------------------------------------- 
    call:bool = False
    for i in range(3):
        json_response = JSONResponse(content=result['template'])
        if json_response.status_code == 200:
            
            data:dict = {'callbackurl':callbackurl, 'user_mode':user_mode, 'user_id': user_id, 'pre_class': prequery_embed_class,
                         'prompt': result['prompt'], 'query':result['query'], 'docs':result['docs'], 
                         's_best_contexts': result['s_best_contexts'], 'llm_model': llm_model, 'extra_id': extra_id}
            
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
# 제품 Q&A
@app.post("/searchdoc2")
async def searchdoc(content: Dict):
    if set_userinfo(content=content["userRequest"], user_mode=22) != 0:
        return

    template = callback_template.product_qa()
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
# [bong][2024-06-03] 개인문서검색

@app.post("/searchuserdoc")
async def searchuserdoc(content: Dict):
    user_id:str = content["userRequest"]["user"]["id"]
    assert user_id, f'user_id is empty'
    
    if set_userinfo(content=content["userRequest"], user_mode=30) != 0:
        return

    settings = myutils.get_options()
    userdocmgr_url = settings['USER_DOC_MGR_URL']
    api_server_url:str = settings['API_SERVER_URL']

    # extraid 를 구함
    res = userdb.select_setting(user_id=user_id)
    extraid:str = ''
    if res != -1: 
        extraid = res['extraid']

    # extraid가 있으면 
    if extraid:
        linkurl = f'{userdocmgr_url}/list?user_id={extraid}'
        print(f'*[searchuserdoc] linkurl: {linkurl}')
        template = callback_template.searchuserdoc(linkurl=linkurl)
        print(f'*[searchuserdoc] template: {template}')
        
    else: # 없으면 설정창으로 이동할수 있는 url 띄워줌.
        linkurl = f'{api_server_url}/setting/form?user_id={user_id}'
        descript = f'개인문서검색을 위해서는 먼저 별칭(extra_id)를 설정해 주셔야 합니다.\n\n아래 설정하기 버튼을 눌러 별칭을 설정해 주십시오.'
        template = callback_template.setting(linkurl=linkurl, descript=descript)    
    
    json_response = JSONResponse(content=template)    
    return json_response
#----------------------------------------------------------------------      
# [bong][2024-06-11] 음악생성
@app.post("/music")
async def searchdoc(content: Dict):
    user_id:str = content["userRequest"]["user"]["id"]
    assert user_id, f'user_id is empty'

    if set_userinfo(content=content["userRequest"], user_mode=31) != 0:
        return

    template = callback_template.music(user_id=user_id)
    json_response = JSONResponse(content=template)
    return json_response

#----------------------------------------------------------------------   
# [bong][2024-06-11] 음악생성후 id를 입력해서 실제 mp4url 얻어오는 함수
@app.get("/music/get")
async def music_get(request:Request, music_id:str, user_id:str):
    
    assert music_id, f'music_id is empty'
    assert user_id, f'user_id is empty'

    host = settings['SUNO_API_SERVER']
    api_url = settings['API_SERVER_URL']
    
    datalist:list = []
    status:int = 0
    text:str = ""
    music_id_list:list = music_id.split(', ')
    
    try:
        # 음악 파일(mp3,mp4) 목록 얻기
        # => 음악 ids 입력후 음악 파일(mp3,mp4) 목록 얻기  
        status, datalist = suno.getfile_by_ids(ids=music_id_list, host=host, max_retries=1)
    except Exception as e:
        msg = f'{error}=>{e}'
        myutils.log_message(f'\t[call_music][error] {msg}')
        status = 102

    if status == 0:
        title = "🎧노래가 완성되었습니다!!\n[노래재생] 버튼을 눌러주세요." 
        text = f'{datalist[0]["title"]}\n{datalist[0]["lyric"]}' # 제목/내용 출력
        ids:list = []
        for data in datalist:
            ids.append(data["video_url"])
            
        template = callback_template.music_success_template(title=title, descript=text, user_id=user_id, music_url=ids)
    else:
        # 답변 설정
        title = "🎧노래 제작중.\n좀더 대기 후 [노래확인] 버튼을 눌러 보세요." 
        text = "🕙노래 제작은 최대 4분 걸릴 수 있습니다.."
        template = callback_template.music_template(title=title, descript=text, api_url=api_url, user_id=user_id, music_ids=music_ids)

    myutils.log_message(f'\t[music_get]==>template:{template}')
    json_response = JSONResponse(content=template)
    return json_response    
#---------------------------------------------------------------------
# music_list.html 로딩
@app.get("/music/list")
async def music_list(request:Request, user_id:str):
    assert user_id, f'user_id is empty'
    status, musiclist = userdb.select_musiclist(user_id=user_id) # 해당 사용자의 musiclist 항목들을 얻어옴.
    
    # Convert date_time to datetime objects and sort the list in descending order
    # date_time 내림차순으로 정렬시킴
    musiclist.sort(key=lambda x: datetime.strptime(x['date_time'], '%Y-%m-%d %H:%M:%S'), reverse=True)

    myutils.log_message(f"\t[music/list]music_list:\n{musiclist}\n")
    return templates.TemplateResponse("music_list.html", {"request": request, "user_id":user_id, "music_list":musiclist})
    
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
    extra_id = form.get("extra_id")
    
    # 변경값으로 셋팅.
    # 해당 사용자의 user_id site를 업데이트
    error = userdb.insert_setting(user_id=user_id, extra_id=extra_id, site=search_site, prequery=int(pre_query), llmmodel=int(llm_model)) 
    myutils.log_message(f"\t[setting]==>error:{error}\n")
    setting_msg:str = ""
    if error == 0:
        setting_msg = "변경되었습니다."
    elif error == 1002:
        setting_msg = "다른 사용자가 사용하는 별칭입니다.다른 별칭을 입력해주세요."
        myutils.log_message(f"\t[setting]==>setting_save fail!=>error:{error}, {setting_msg}\n")
        extra_id = ""
    else:
        setting_msg = "에러가 발생하였습니다."
        extra_id = ""
        myutils.log_message(f"\t[setting]==>setting_save fail!=>error:{error}, {setting_msg}\n")
        
    return templates.TemplateResponse("setting.html", {"request": request, "user_id":user_id, "extra_id":extra_id, "search_site": search_site, 
                                                       "pre_query": int(pre_query), "llm_model": int(llm_model), 
                                                       "setting_msg": setting_msg })
#----------------------------------------------------------------------    
# setting.html 로딩    
@app.get("/setting/form")
async def setting_form(request:Request, user_id:str):
    assert user_id, f'user_id is empty'
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site를 얻어옴
    
    search_site:str = "naver" # 웹검색 사이트 (기본은 naver)
    pre_query:int=1   # 예전 유사 질문 검색(기본=1(검색함))
    llm_model:int=0   # [bong][2024-04-18] llm 모델 (0=gpt, 1=gamma(구글))
    extraid_str:str = ""
    if setting != -1 and setting['site']:
        search_site = setting['site']
        pre_query = setting['prequery']
        llm_model = setting['llmmodel']
        extraid_str = setting['extraid'] # [bong][2024-06-03] 별칭(Extra id) 
        
    #myutils.log_message(f"\t[setting]==>setting_form=>user_id:{user_id}, search_site:{search_site}, prequery:{pre_query}\n")
    
    return templates.TemplateResponse("setting.html", {"request": request, "user_id":user_id, "extra_id":extraid_str,
                                                       "search_site": search_site, "pre_query":pre_query, "llm_model":llm_model})
#----------------------------------------------------------------------
@app.post("/setting")
async def setting(content: Dict):
    user_id:str = content["userRequest"]["user"]["id"]
    assert user_id, f'user_id is empty'
    
    api_server_url:str = settings['API_SERVER_URL']
    
    search_site:str = "naver" # 웹검색 사이트 (기본은 naver)
    pre_query:int=1   # 예전 유사 질문 검색(기본=1(검색함))
    llm_model:int=0   # llm 모델 종류(0=gpt, 1=구글 gemma, 2=구글 gemini)
    llm_model_list:list = ['GPT','구글 Gemma', '구글 Gemini']   
    pre_query_str:str = '검색함'
    user_mode_list:list = ['회사문서검색(수동)','웹검색(1)','채팅하기(2)', '이미지생성(3)']   
    user_mode_str:str = "없음"
    llm_model_str:str = ""
    extraid_str:str = ""
    
    setting = userdb.select_setting(user_id=user_id) # 해당 사용자의 site를 얻어옴
    #myutils.log_message(f"\t[setting]==>setting:{setting}\n")
    
    user_mode=userdb.select_user_mode(user_id=user_id)
    if user_mode == -1:
        user_mode = 0

    if user_mode == 22:
        user_mode_str = 'EZis-C Q&A'
    elif user_mode == 23:
        user_mode_str = '회사문서검색(GPT)'
    elif user_mode == 30:
        user_mode_str = '개인문서검색'
    elif user_mode == 31 or user_mode == 32 or user_mode == 33:
        user_mode_str = '노래만들기'
    else:
        user_mode_str = user_mode_list[user_mode]
    
    if setting != -1 and setting['site']:
        search_site = setting['site']
        pre_query = setting['prequery']
        llm_model = setting['llmmodel']
        # [bong][2024-06-03] 별칭(Extra id) 
        extraid_str = setting['extraid']
        
    if pre_query != 1:
        pre_query_str:str = '검색안함'

    # [bong][2024-04-18] llm 모델명 설명
    if llm_model > 2:
        llm_model = 0
    llm_model_str = llm_model_list[llm_model]


    linkurl = f'{api_server_url}/setting/form?user_id={user_id}'
    descript = f'🧒 사용자ID: {user_id}\n\n😁별칭(Extra ID): {extraid_str}\n\n🕹 현재 동작모드: {user_mode_str}\n💬 에전유사 질문검색: {pre_query_str}\n🌐 웹검색 사이트: {search_site}\n😀AI 모델: {llm_model_str}\n\n예전유사 질문검색, 웹검색 사이트, AI 모델등이 변경을 원하시면 설정하기를 눌러 변경해 주세요.'
    
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