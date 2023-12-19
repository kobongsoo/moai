import os
import time
import asyncio
import threading
import httpx
import sys

def chatbot_quiz(settings:dict, data:dict, instance:dict, result:dict):
    template:dict = {}; prompt:str = ''; error:int=0

    user_id = data['userid']
    query = data['query']
    context = data['quiz_res']
    
    prefix_query = query[0]
    if prefix_query == '?' or prefix_query == '!' or prefix_query == '@':
        query = query[1:] 
        
    assert user_id, f'user_id is empty'
    assert query, f'query is empty'

    webscraping = instance['webscraping']
    myutils = instance['myutils']
    id_manager = instance['id_manager']
    callback_template = instance['callback_template']

    # 퀴즈 만들 context에 길이에 따라서 퀴즈 계수를 (2,3,4) 설정함.
    quiz_context:str = context[0]['response']
    quiz_create_num = 2
    if len(quiz_context) > 400:
        quiz_create_num = 4
    elif len(quiz_context) > 250:
        quiz_create_num = 3
            
    prompt = settings['PROMPT_QUIZ'].format(context=quiz_context, quiz_create_num=quiz_create_num)  # 퀴즈문제를 몃개만들지 prompt 구성
    query = "❓돌발퀴즈.."

    search_str = "❓돌발퀴즈 준비중.."
    template = callback_template.usecallback_template(text=search_str, usercallback=True)
    
    result['prompt'] = prompt
    result['query'] = query
    result['template'] = template
        
    return result
#-----------------------------------------------------------
# 퀴즈 템플릿 얻기.
#-----------------------------------------------------------
def get_quiz_template(quiz_dict:dict, instance:dict):

    template:dict = {}; user_mode:int = 0
    response:dict = {'template': template, 'quiz':[]}
    
    user_id = quiz_dict['userid']
    query = quiz_dict['query']
    
    assert user_id, f'user_id is empty'
  
    myutils = instance['myutils']
    userdb = instance['userdb']
    callback_template = instance['callback_template']
    quiz_callback_template = instance['quiz_callback_template']

    if query.startswith("?돌발퀴즈."):
        res, quiz_num = userdb.select_quiz(userid=user_id, type=100) # 저장된 최근 response를 얻어옴.
        if res != -1:
            if len(res) > 0:
                user_mode = 8

        if user_mode != 8:
            template = callback_template.simpletext_template(text = "⚠️다음기회에..\n내용이 없어 돌발퀴즈를 만들 수 없습니다.")
    else:
        # '?퀴즈시작' => db에서 첫번째 퀴즈문제 얻어와서 문제 보여줌.     
        res, quiz_num=userdb.select_quiz(userid=user_id, type=1)
        #myutils.log_message(f'\t[chatbot3]==>퀴즈:res:{res}')
            
    if res != -1:
        if query.startswith("?퀴즈시작."):
            quiz_query=res[0]['query']  # 1번째 문제 뽑아옴.
            template = quiz_callback_template.quiz_question(quiz_query={'query':quiz_query})
            myutils.log_message(f'\t퀴즈시작:template:{template}')
        # 퀴즈 정답을 1,2,3,4 선택한 경우
        elif len(res) > 0:
            if query=="1번" or query=="2번" or query=="3번" or query=="4번":
                user_answer = query[0]     # 1번, 2번, 3번, 4번 중 맨앞 1,2,3,4만 뽑아냄
                answer:dict={'answer':res[0]['answer'], 'info': res[0]['info'], 'user_answer': user_answer} # quiz_answer 설정                         
                template=quiz_callback_template.quiz_answer_info(quiz_num=quiz_num, quiz_count=res[0]['type'], quiz_answer=answer)  # 정답 template 만듬    
                userdb.delete_quiz_type(userid=user_id, type=res[0]['type']) #해당 type 퀴즈db만 삭제
                myutils.log_message(f'\t퀴즈번호선택:template:{template}')
                
            elif query.startswith("?다음문제"):
                quiz_query=res[0]['query']  # 1번째 문제 뽑아옴.
                template = quiz_callback_template.quiz_question(quiz_query={'query':quiz_query})
                myutils.log_message(f'\t다음문제:template:{template}')
                
            elif query.startswith("?이제퀴즈그만"):
                userdb.delete_quiz_all(userid=user_id) # 모든 퀴즈 db 삭제
                template = callback_template.simpletext_template(text = f"⚠️퀴즈를 중지합니다.")
                myutils.log_message(f'\t이제퀴즈그만:template:{template}')
                
    response['quiz'] = res
    response['template'] = template
    return response


    