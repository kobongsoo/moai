import os
import time
import asyncio
import threading
import httpx
import sys

sys.path.append('..')
from utils import es_embed_query, make_prompt

def chatbot_text_search(settings:dict, data:dict, instance:dict, result:dict, es_index_name:str=''):

    template:dict = {}; prompt:str = ''; error:int=0; docs:list=[]

    user_id = data['userid']
    query = data['query']
    bi_encoder = data['bi_encoder']
    rerank_model = data['rerank_model'] # [bong][2024-05-21] ReRank 모델 설정
    
    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:] 
    
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    # 입력된 es_index_name 이 있으면 esindex를 설정하고, 없으면 setting에 settings['ES_INDEX_NAME'] 값을 설정함
    esindex = es_index_name if es_index_name else settings['ES_INDEX_NAME']  
    assert esindex, f'esindex is empty'
    
    search_size:int = settings['ES_SEARCH_DOC_NUM']      # 회사본문 검색 계수
    qmethod:int = settings['ES_Q_METHOD']
    use_rerank = settings['USE_RERANK'] # [bong][2024-05-21] ReRank 사용유.무
    
    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']
    
    try:
        # es로 임베딩 쿼리 실행      
        error_str, docs = es_embed_query(settings=settings, esindex=esindex, query=query, 
                                         search_size=search_size, bi_encoder=bi_encoder, qmethod=qmethod)

        #==============================================================
        # [bong][2024-05-21] ReRank 사용일때 처리
        #==============================================================
        if use_rerank == 1:
            rerank_rfile_texts = [doc['rfile_text'] for doc in docs] # docs에서 rfile_text 만 뽑아내서 리스트 만듬
            rerank_rfile_names = [doc['rfile_name'] for doc in docs] # docs에서 rfile_name 만 뽑아내서 리스트 만듬

            # 스코어 구함.
            rerank_scores = rerank_model.compute_score(query=query, contexts=rerank_rfile_texts)

            # 세 리스트를 결합하여 하나의 리스트로 생성
            rerank_combined_list = list(zip(rerank_scores, rerank_rfile_texts, rerank_rfile_names))

            # scores 값을 기준으로 내림차순으로 정렬
            rerank_sorted_list = sorted(rerank_combined_list, key=lambda x: x[0], reverse=True)
            
            # 정렬된 리스트를 원하는 형식의 딕셔너리 리스트로 변환
            rerank_docs = [{'rfile_name': name, 'rfile_text': text, 'score': score} for score, text, name in rerank_sorted_list]

            prompt, embed_context = make_prompt(settings=settings, docs=rerank_docs, query=query)
            print(f'\n\n\t\t==>*RERANK PROMPT:\n\t\t{prompt}\\n\n================')
            #==============================================================
        else:    
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
    