import os
import time

def chatbot_check(kakaoDict:dict, instance:dict):

    template:dict = {}
    response:dict = {'error': 0, 'template': template}
    
    myutils = instance['myutils']
    id_manager = instance['id_manager']
    userdb = instance['userdb']
    callback_template = instance['callback_template']
    
    kakao_userRequest = kakaoDict["userRequest"]  
    query:str = kakao_userRequest["utterance"]  # 질문
    callbackurl:str = kakao_userRequest["callbackUrl"] # callbackurl
    user_id:str = kakao_userRequest["user"]["id"]

    assert query, f'Error:query is empty'
    assert user_id, f'Error:user_id is empty'
    assert callbackurl, f'Error:callbackurl is empty'

    myutils.log_message(f"=" * 80)
    myutils.log_message(f"\t[chatbot_check][start]=>kakaoDict['userRequest']:\n{kakao_userRequest}")
    
    # 쿼리가 이미지인지 파악하기 위해 type을 얻어옴.'params': {'surface': 'Kakaotalk.plusfriend', 'media': {'type': 'image', 'url':'https://xxxx'}...}
    query_format:str = ""; ocr_url:str = ""
    if 'media' in kakao_userRequest['params'] and 'type' in kakao_userRequest['params']['media']:
        query_format = kakao_userRequest['params']['media']['type']
    #-----------------------------------------------------------
    # id_manager 에 id가 존재하면 '이전 질문 처리중'이므로, return 시킴
    # 응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 해당 user_id 가 있는지 검색
    if id_manager.check_id_exists(user_id):
        myutils.log_message(f't\[chatbot_check] 이전 질문 처리중:{user_id}\n')
        response['error'] = 101
        return response
    #-----------------------------------------------------------        
    # 동영상이나 입력은 차단
    if query_format != "" and query_format != "image":
        template = callback_template.simpletext_template(text = f'⚠️동영상은 입력 할수 없습니다.')
        myutils.log_message(f't\[chatbot_check] 동영상은 입력 할수 없습니다:{user_id}\n')
        response['error'] = 5
        return response
    #-----------------------------------------------------------
    # [bong][2023-12-11] 채팅모드에서 '?새로운대화시작' 문자열이 들어오면=>이전 질문 내용 모두 제거하고 return
    if query.startswith("?새로운대화시작"):
        userdb.delete_assistants(user_id=user_id)   # 이전 질문 내용 모두 제거
        template = callback_template.simpletext_template(text = f'💬새로운 대화를 시작합니다.')
        myutils.log_message(f't\[chatbot_check] 새로운 대화를 시작합니다.:{user_id}\n')
        response['error'] = 1002
        response['template'] = template
        return response
    #-----------------------------------------------------------
    # 1글자 특수문자 들어오면 return 시킴.
    if query == '?' or query == '!' or query == '@':
        myutils.log_message(f't\[chatbot_check] 특수문자{query}만 입력됨.:{user_id}\n')
        response['error'] = 102
        return response
    #-----------------------------------------------------------   
    
    # id_manager 에 id 추가.  응답 처리중에는 다른 질문할수 없도록 lock 기능을 위해 user_id 추가함.
    id_manager.add("0", user_id) # mode와 user_id 추가
    
    return response
    