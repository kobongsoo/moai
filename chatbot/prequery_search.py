import os
import time

def get_prequery_search_template(prequery_dict:dict, instance:dict):

    template:dict = {}

    user_id = prequery_dict['userid']
    query = prequery_dict['query']
    user_mode = prequery_dict['usermode']
    prequery_embed_class = prequery_dict['pre_class']
    set_prequery = prequery_dict['set_prequery']
    
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    myutils = instance['myutils']
    userdb = instance['userdb']
    prequery_embed = instance['prequery_embed']
    callback_template = instance['callback_template']
    
    prequery_search = True   # True=이전질문 검색함.  
    if query[0] == '?' or query[0] == '!' or query[0] == '@':
        prequery_search = False
    elif user_mode==3 or user_mode==4 or user_mode==5 or user_mode==6 or user_mode==7:  # 이전 질문 검색(회사본문검색=0, 웹문서검색=1, 채팅=2) 일때만 
        prequery_search = False
        
    # 이전 질문 검색(회사본문검색=0, 웹문서검색=1) 일때만 
    if prequery_search == True and set_prequery == 1: 
        embed_class = 0
        if user_mode < 3:
            embed_class = user_mode
        prequery_docs = prequery_embed.embed_search(query=query, classification=prequery_embed_class[embed_class])
        if len(prequery_docs) > 0:
            prequery_score = prequery_docs[0]['score']
            prequery_response = prequery_docs[0]['response']
            prequery = prequery_docs[0]['query']
            prequery_id = prequery_docs[0]['_id']
            myutils.log_message(f'\t[get_prequery_search_template]==>이전질문:{prequery}(score:{prequery_score}, id:{prequery_id})\n이전답변:{prequery_response}')

            template = callback_template.pre_answer(query=query, prequery=prequery, prequery_response=prequery_response, user_mode=user_mode, prequery_score=prequery_score)

            if template:
                # 유사한 질문이 있으면 추가
                callback_template.similar_query(prequery_docs=prequery_docs, template=template)                 

    return template
    