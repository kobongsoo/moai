import os
import time
import asyncio
import threading
import httpx
import sys

sys.path.append('..')
from utils import es_embed_query, make_prompt

def chatbot_text_search(settings:dict, data:dict, instance:dict, result:dict):

    template:dict = {}; prompt:str = ''; error:int=0; docs:list=[]

    user_id = data['userid']
    query = data['query']
    bi_encoder = data['bi_encoder']

    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:] 
    
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    esindex:str = settings['ES_INDEX_NAME']              #"qaindex"  # qaindex    
    search_size:int = settings['ES_SEARCH_DOC_NUM']      # 회사본문 검색 계수
    qmethod:int = settings['ES_Q_METHOD']
    
    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']
    
    try:
        # es로 임베딩 쿼리 실행      
        error_str, docs = es_embed_query(settings=settings, esindex=esindex, query=query, 
                                            search_size=search_size, bi_encoder=bi_encoder, qmethod=qmethod)
        
        # prompt 생성 => min_score 보다 작은 conext는 제거함.
        prompt, embed_context = make_prompt(settings=settings, docs=docs, query=query)
            
    except Exception as e:
        myutils.log_message(f'\t[chatbot_text_search]==>async_es_embed_query fail=>{e}')
        id_manager.remove_id_all(user_id) # id 제거
        result['error'] = 1001
        return result

    # 컨텍스트가 없으면. 임베딩을 못찾은 것이므로, bFind_docs=False로 설정
    if len(embed_context) < 2:
        id_manager.remove_id_all(user_id) # id 제거
        text = "⚠️질문에 맞는 내용을🔍찾지 못했습니다. 질문을 다르게 해 보세요."
        template = callback_template.simpletext_template(text = text)
        result['error'] = 1002
    else:
        # 답변 설정
        text = "🔍회사문서검색 완료. 답변 대기중.." 
        template = callback_template.usecallback_template(text=text, usercallback=True)

    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
    result['docs'] = docs
        
    return result
    