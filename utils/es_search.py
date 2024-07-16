import torch
import time
import os
import numpy as np
from tqdm.notebook import tqdm

import asyncio
from elasticsearch import Elasticsearch

from .es_embed import embedding
from .algorithm import weighted_reciprocal_rank_fusion

#---------------------------------------------------------------------------
# ES 평균 쿼리 스크립트 구성
# => 1문서당 10개의 벡터가 있는 경우 10개의 벡터 유사도 평균 구하는 스크립트
# => 아래 make_max_query_script 보다 엄청 정확도 떨어짐. (max=83%, avg=50%)
# -in: query_vector = 1차원 임베딩 벡터 (예: [10,10,1,1, ....]
# -in: vectornum : ES 인덱스 벡터 수
# -in: vectormag : 사용하지 않음
#---------------------------------------------------------------------------
def make_avg_query_script(query_vector, vectornum:int=10, vectormag:float=0.8, uid_list:list=None)->str:
    # 문단별 10개의 벡터와 쿼리벡터를 서로 비교하여 최대값 갖는 문단들중 가장 유사한  문단 출력
    # => script """ 안에 코드는 java 임.
                        
    # uid_list가 있는 경우에는 해당하는 목록만 검색함
    if uid_list:
        query = { "bool" :{ "must": [ { "terms": { "rfile_name": uid_list } } ] } }
    else: # uid_list가 있는 경우에는 해당하는 목록만 검색함
        query = { "match_all" : {} }
    
    script_query = {
        "script_score":{
             "query":query,
                "script":{
                    "source": """
                    
                      float sqrt(float number) {
                        float guess = number / 2.0f;
                        float epsilon = 0.00001f;  // 원하는 정확도
                        while (Math.abs(guess * guess - number) >= epsilon) {
                            guess = (guess + number / guess) / 2.0f;
                        }
                      return guess;
                      }
                 
                      float queryVector_sum_size = 0.0f;
                      // 쿼리벡터의 크기를 구함.->벡터제곱근 구하고 루트(sqrt) 처리                      
                      for (int j = 0; j < params.queryVector.length; j++) {
                          queryVector_sum_size += params.queryVector[j] * params.queryVector[j];
                      } 
                      
                      float queryVector_size = sqrt(queryVector_sum_size);
                      float avg_score = 0;
                      float total_score = 0;
                      for(int i = 1; i <= params.VectorNum; i++) 
                      {
                          float[] v = doc['vector'+i].vectorValue; 
                          float vm = doc['vector'+i].magnitude;  
                          if (v[0] != 0)
                          {
                            // dot(내적) 2벡터간 내적을 구함.
                            float dotProduct = 0.0f;
                            
                            for(int j = 0; j < v.length; j++) 
                            {
                                dotProduct += v[j] * params.queryVector[j];
                            }
                            
                            // 스코어를 구함 = dot/(벡터1크기*쿼리벡터크기)
                            float score = dotProduct / (vm * queryVector_size);
                              
                            if (score < 0) 
                            {
                                score = 0
                            }
                            total_score += score;
                          }
                      }
                      avg_score = total_score / params.VectorNum;
                      if (avg_score < 0) {
                        avg_score = 0;
                      }
                      return avg_score
                    """,
                "params": 
                {
                  "queryVector": query_vector,  # 벡터임베딩값 설정
                  "VectorNum": vectornum        # 벡터 수 설정
                }
            }
        }
    }
    
    return script_query
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# ES MAX 쿼리 스크립트 구성
# => 1문서당 10개의 벡터 중에서 가장 유사도가 큰 1개의 벡터 유사도 측정하는 쿼리
# -in: query_vector = 1차원 임베딩 벡터 (예: [10,10,1,1, ....]
# -in: vectornum : ES 인덱스 벡터 수
# -in: vectormag : 사용하지 않음
#---------------------------------------------------------------------------
def make_max_query_script(query_vector, vectornum:int=10, vectormag:float=0.8, uid_list:list=None)->str:
    # 문단별 10개의 벡터와 쿼리벡터를 서로 비교하여 최대값 갖는 문단들중 가장 유사한  문단 출력
    # => script """ 안에 코드는 java 임.
                        
    # uid_list가 있는 경우에는 해당하는 목록만 검색함
    if uid_list:
        query = { "bool" :{ "must": [ { "terms": { "rfile_name": uid_list } } ] } }
    else: # uid_list가 있는 경우에는 해당하는 목록만 검색함
        query = { "match_all" : {} }
    
    script_query = {
        "script_score":{
             "query":query,
                "script":{
                    "source": """
                    
                      float sqrt(float number) {
                        float guess = number / 2.0f;
                        float epsilon = 0.00001f;  // 원하는 정확도
                        while (Math.abs(guess * guess - number) >= epsilon) {
                            guess = (guess + number / guess) / 2.0f;
                        }
                      return guess;
                      }
                 
                      float queryVector_sum_size = 0.0f;
                      // 쿼리벡터의 크기를 구함.->벡터제곱근 구하고 루트(sqrt) 처리                      
                      for (int j = 0; j < params.queryVector.length; j++) {
                          queryVector_sum_size += params.queryVector[j] * params.queryVector[j];
                      } 
                      
                      float queryVector_size = sqrt(queryVector_sum_size);
                      float max_score = 0.0f; 
                      for(int i = 1; i <= params.VectorNum; i++) 
                      {
                          float[] v = doc['vector'+i].vectorValue; 
                          float vm = doc['vector'+i].magnitude;  
                          if (v[0] != 0)
                          {
                            // dot(내적) 2벡터간 내적을 구함.
                            float dotProduct = 0.0f;
                            
                            for(int j = 0; j < v.length; j++) 
                            {
                                dotProduct += v[j] * params.queryVector[j];
                            }
                            
                            // 스코어를 구함 = dot/(벡터1크기*쿼리벡터크기)
                            float score = dotProduct / (vm * queryVector_size);
                              
                            if(score > max_score) 
                            {
                                max_score = score;
                            }
                          }
                      }
                      return max_score
                    """,
                "params": 
                {
                  "queryVector": query_vector,  # 벡터임베딩값 설정
                  "VectorNum": vectornum        # 벡터 수 설정
                }
            }
        }
    }
    
    return script_query
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# ES 기본 vector 쿼리 구성
#---------------------------------------------------------------------------
def make_query_script(query_vector, uid_list:list=None)->str:
    # 문단별 10개의 벡터와 쿼리벡터를 서로 비교하여 최대값 갖는 문단들중 가장 유사한  문단 출력
    # => script """ 안에 코드는 java 임.
    # => "queryVectorMag": 0.1905 일때 100% 일치하는 값은 9.98임(즉 10점 만점임)
                        
    # uid_list가 있는 경우에는 해당하는 목록만 검색함
    if uid_list:
        query = { "bool" :{ "must": [ { "terms": { "rfile_name": uid_list } } ] } }
    else: # uid_list가 있는 경우에는 해당하는 목록만 검색함
        query = { "match_all" : {} }
    
    script_query = {
        "script_score":{
            "query":query,
            "script":{
                #"source": "cosineSimilarity(params.queryVector, doc['vector1']) + 1.0",  # 뒤에 1.0 은 코사인유사도 측정된 값 + 1.0을 더해준 출력이 나옴
                "source": "cosineSimilarity(params.queryVector, 'vector1') + 1.0",
                "params": {"queryVector": query_vector}
            }
        }
    }
    
    return script_query

#---------------------------------------------------------------------------
#쿼리에 대해 일반검색해서 임베딩 검색할 후보군 10개 목록 uids를 얻는 함수
#---------------------------------------------------------------------------
def es_search_uids(es, esindex:str, uid_min_score:int, size:int=10, data=None):
    if data is None: #모든 데이터 조회
        data = {"match_all":{}}
    else:
        data = {"match": data}
        
    body = {
        "size": size,
        "query": data,
        "_source":{"includes": ["rfile_name","rfile_text"]}
    }
    
    response = None
    response = es.search(index=esindex, body=body)
    
    #print(f'=>후보군 uid_min_score:{uid_min_score}')
    #print(f'=>후보군 list:{response}\n')
    
    rfilename = []
    count = 0
    docs = []
    
    for hit in response["hits"]["hits"]: 
        tmp = hit["_source"]["rfile_name"]

        # 중복 제거
        if tmp and tmp not in rfilename:
            rfilename.append(tmp)
            doc = {}  #dict 선언
            score = hit["_score"]
            if score > uid_min_score:  # 6 이상일때만 스코어 계산
                doc['rfile_name'] = hit["_source"]["rfile_name"]      # contextid 담음
                doc['rfile_text'] = hit["_source"]["rfile_text"]      # text 담음.
                doc['score'] = score
                docs.append(doc)
                count += 1
                # 후보군 스코어와 text 출력해봄
                #print(f'score:{score}, text:{doc["rfile_text"]}\n')
    
    uids = []
    for doc in docs:
        uids.append(doc['rfile_name'])

    return uids, docs
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# ES 임베딩 벡터 쿼리 실행 함수
# - in : esindex=인덱스명, query=쿼리 , search_size=검색출력계수
# - option: qmethod=0 혹은 1 혹은 2(0=max벡터 구하기, 1=평균벡터 구하기, 2=임베딩벡터가 1개인 경우 (default=0)), uid_list=검색할 uid 리스트(*엠파워에서는 검색할 문서id를 지정해서 검색해야 검색속도가 느리지 않음)
#---------------------------------------------------------------------------
def es_embed_query(settings:dict, esindex:str, query:str, 
                   search_size:int, bi_encoder, qmethod:int=0, 
                   uids:list=None):
    
    error: str = 'success'
    
    query = query.strip()
    
    #print(f'search_size: {search_size}')
    es_url = settings['ES_URL']
    vector_mgr = settings['ES_SEARCH_VECTOR_MAG']
    float_type = settings['E_FLOAT_TYPE']
    vector_num = settings['NUM_CLUSTERS']

    # 회사문서검색전 BM25 후보군 검색 & RRF 알고리즘 적용 유.무 설정
    uid_search = settings['ES_UID_SEARCH'] # BM25검색: 임베딩 검색하기전 후보군 검색할지 안할지(0=검색안함/1=BM25 검색함+후보군적용/2=BM25 검색함+ BM25와 임베딩 순위를 RRF(상호 순위 융합) 적용함)
    uid_min_score = settings['ES_UID_MIN_SCORE']# 후보군 검색 스코어 xx이하면 제거 =>안녕하세요 검색하면 1.1정도 검색됨(벡터 1개일때 =>5.0),클러스터링10개 일때=>11.0
    uid_search_len = settings['ES_UID_SEARCH_LEN'] # 후보군 검색할 계수
    uid_bm25_weigth = settings['ES_RRF_BM25_WEIGTH'] # ES_UID_SEARCH=2 일때 BM25 가중치(EMBED와 합쳐서 2가되어야 함)
    uid_embed_weigth = settings['ES_RRF_EMBED_WEIGTH'] # ES_UID_SEARCH=2 일때 EMBED 가중치

    #print(f'\t\t===>uid_search: {uid_search}, uid_min_score: {uid_min_score}, uid_search_len:{uid_search_len}, uid_bm25_weigth:{uid_bm25_weigth}, uid_embed_weigth:{uid_embed_weigth}')

    # 1.elasticsearch 접속
    es = Elasticsearch(es_url)   
    
    if not query:
        error = 'query is empty'
    elif search_size < 1:
        error = 'search_size < 1'
    elif not es.indices.exists(esindex):
        error = 'esindex is not exist'
    elif qmethod < 0 or qmethod > 2:
        error = 'qmenthod is not variable'
    elif vector_num < 1:
        error = 'vector_num is not variable'
    elif uid_search_len < 1:
        error = 'uid_search_len is not variable'
        
    if error != 'success':
        return error, None
   
    #print(f'vector_num: {type(vector_num)}/{vector_num}')

    #  후보군 검색이 설정된 경우에 es 일반검색 해서 후보군 리스트 뽑아냄.(*후보군이 있으면 일반검색 하지 않음)
    BM25_docs:list = []
    if uid_search == 1 or uid_search == 2:        
        if uids == None:
            #print(f'[후보군 검색] Q:{query}')
            
            #* es로 쿼리해서 후보군 추출.
            data = {'rfile_text': query}
            uids, BM25_docs = es_search_uids(es=es, esindex=esindex, uid_min_score=uid_min_score, size=uid_search_len, data=data)

        # ==================================================================
        # [bong][2024-05-17] RRP(Reciprocal Rank Fusion: 상호 순위 융합) 일때는 uids=None 으로 해야 
        # 뒤에 임베딩 검색 쿼리 만들때 후보군으로 지정하지 않고 검색됨.
        # ==================================================================
        if uid_search == 2:
            #print(f'\t==>[RRF] es_embed_query:uids:{uids}')
            uids = []
        # ==================================================================
            
        #print(f'\t==>es_embed_query:uids:{uids}, qmethod: {qmethod}')
        
        if uid_search == 1 and len(uids) < 1:
            return error, BM25_docs # 쿼리,  rfilename, rfiletext, 스코어 리턴         

    # 2. 검색 문장 embedding 후 벡터값 
    # 쿼리들에 대해 임베딩 값 구함
    start_embedding_time = time.time()
    embed_query = embedding([query], bi_encoder, float_type)
    end_embedding_time = time.time() - start_embedding_time
    #print("*embedding time: {:.2f} ms".format(end_embedding_time * 1000)) 
    #print(f'*embed_querys.shape:{embed_query.shape}\n')
        
    # 3. 임베딩 쿼리 만듬
    # - 쿼리 1개만 하므로, embed_query[0]으로 입력함.
    if qmethod == 0:
        script_query = make_max_query_script(query_vector=embed_query[0], vectormag=vector_mgr, vectornum=int(vector_num), uid_list=uids) # max 쿼리를 만듬.
    elif qmethod == 1:
        script_query = make_avg_query_script(query_vector=embed_query[0], vectormag=vector_mgr, vectornum=int(vector_num), uid_list=uids) # 평균 쿼리를 만듬.
    else:
        script_query = make_query_script(query_vector=embed_query[0], uid_list=uids) # 임베딩 벡터가 1개인경우=>기본 쿼리 만듬.
        
    #print(f'\t\t===>script_query:{script_query}\n\n')

    # 4. 실제 ES로 임베딩 검색 쿼리 날림
    response = es.search(
        index=esindex,
        body={
            #"size": search_size * 3, # 3배 정도 얻어옴
            "size": search_size,
            "query": script_query,
            "_source":{"includes": ["rfile_name","rfile_text"]}
        }
    )

    # 5. 결과 리턴
    # - 쿼리 응답 결과값에서 _id, _score, _source 등을 뽑아내고 내림차순 정렬후 결과값 리턴
    #print(f'\t\t===>*임베딩 결과:\n{response}\n')
    
    rfilename = []
    count = 0
    embed_docs:list = []
    for hit in response["hits"]["hits"]: 
        tmp = hit["_source"]["rfile_name"]
        
        # 중복 제거
        if tmp and tmp not in rfilename:
            rfilename.append(tmp)
            doc = {}  #dict 선언
            doc['rfile_name'] = hit["_source"]["rfile_name"]      # contextid 담음
            doc['rfile_text'] = hit["_source"]["rfile_text"]      # text 담음.
            doc['score'] = hit["_score"]
            embed_docs.append(doc)
            
            count += 1
            if count >= search_size:
                break

    # ==================================================================
    # [bong][2024-05-17] RRP(Reciprocal Rank Fusion: 상호 순위 융합) 처리
    # => BM25_docs 와 embed_docs를 가지고 RRF(상호 순위 융합) 구함.
    # ==================================================================
    if uid_search == 2:
        print(f'\t==>[RRF] embed_docs 길이: {len(embed_docs)}, BM25_docs 길이:{len(BM25_docs)}')
        
        if len(embed_docs) > 0 and len(BM25_docs) > 0:
            
            embed_docs_name = [doc['rfile_name'] for doc in embed_docs]
            BM25_docs_name = [doc['rfile_name'] for doc in BM25_docs]

            print(f'\t==>[RRF] embed_docs_name: {embed_docs_name}')
            print(f'\t==>[RRF] BM25_docs_name: {BM25_docs_name}')
            
            # RRF를 구하는데, 가중치는 똑같이 1,1로 함.
            # 출력은 튜플('name', 스코어) 을 담고 있는 리스트로 반환됨.
            # =>예) [('a', 0.8333333333333333), ('b', 0.5), ('d', 0.5), ('c', 0.3333333333333333)]
            RRF_scores=weighted_reciprocal_rank_fusion(lists=[embed_docs_name, BM25_docs_name], weights=[uid_embed_weigth, uid_bm25_weigth])

            print(f'\t==>[RRF] RRF_scores: {RRF_scores}')
            
            # BM25_docs 와 embed_docs 두 리스트를 합쳐서 하나의 딕셔너리로 만듬.
            combined_docs = {doc['rfile_name']: doc for doc in embed_docs + BM25_docs}

            #print(f'\t==>[RRF] combined_docs: {combined_docs}\n\n')
            
            # RRF_scores에 있는 name과 일치하는 rfile_text 값을 combined_docs 리스트에서 찾아서, RRF_docs 리스트에 추가함.
            RRF_docs = []
            for name, RRF_score in RRF_scores:
                if name in combined_docs:
                    RRF_doc = {
                        'rfile_name': combined_docs[name]['rfile_name'],  # combined_docs name
                        'rfile_text': combined_docs[name]['rfile_text'],  # combined_docs rfile_text
                        'score': RRF_score
                    }
                    RRF_docs.append(RRF_doc)

            #print(f'\t==>[RRF] RRF_docs:\n{RRF_docs}\n\n')
            
            return error, RRF_docs
    # ==================================================================
        
    return error, embed_docs # 쿼리,  rfilename, rfiletext, 스코어 리턴 

#---------------------------------------------------------------------------
# 비동기 ES 임베딩 벡터 쿼리 실행 함수
#---------------------------------------------------------------------------
async def async_es_embed_query(settings:dict, esindex:str, query:str, search_size:int, bi_encoder, qmethod:int, uids:list=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, es_embed_query, settings, esindex, query, search_size, bi_encoder, qmethod, uids)
#---------------------------------------------------------------------------


# main    
if __name__ == '__main__':
    main()