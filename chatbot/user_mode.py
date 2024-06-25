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

    
    # [bong][2024-06-11] 31=text로 음악생성, 32=이미지로 음약생성, 33=^노래확인^, 34=getsuno=남은용량얻기
    if query.startswith("getsuno"):
        user_mode = 34
        return user_mode
        
    if query.startswith("^노래확인^"):
        user_mode = 33  
        return user_mode

    if prefix_query == '🎼':  # 🎼 들어오면->gpt_4o_vision에서 이미지분석후 음악생성 클릭한 경우임.=> 이때는 text가 드러오므로 31로 리턴하면됨.
        user_mode = 31
        return user_mode
        
    if user_mode == 31:
        if query_format == "image":
            user_mode = 32
        else:
            user_mode = 31
        return user_mode
           
    if user_mode == -1:
        user_mode = 0

    # 쿼리가 url 이면 사용자 모드는 5(URL 요약)로 설정
    if prefix_query == '?':
        url_query = query[1:]
    else:
        url_query = query
        
    if webscraping.is_url(url_query) == True and query_format == "":
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
    