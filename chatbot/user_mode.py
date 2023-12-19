import os
import time

def get_user_mode(usermode_dict:dict, instance:dict):

    user_mode:int = 0

    user_id = usermode_dict['userid']
    query = usermode_dict['query']
    query_format = usermode_dict['query_format']

    assert user_id, f'user_id is empty'
    assert query, f'query is empty'
    
    userdb = instance['userdb']
    webscraping = instance['webscraping']

    prefix_query = query[0]
        
    # 사용자 모드(0=본문검색, 1=웹문서검색, 2=채팅) 얻어옴.
    user_mode = userdb.select_user_mode(user_id)
    if user_mode == -1:
        user_mode = 0
        
    # 쿼리가 url 이면 사용자 모드는 5(URL 요약)로 설정
    if webscraping.is_url(query) == True and query_format == "":
        user_mode = 5    
        
    # 입력 format이 image 혹은  이미지에서 글자다시 검출인경우(prefix_query == '@').. 사용자 모드는 6(이미지 OCR)로 설정
    if query_format == "image" or prefix_query == '@':
        user_mode = 6  
     
    # prefix_query1 이 '!' 이면 '이미지내용 요약' 임.
    if prefix_query == '!':
        user_mode = 7

    #[bong][2023-12-12] '?돌발퀴즈' 이면
    if query.startswith("?돌발퀴즈."):
        user_mode = 8

    return user_mode
    