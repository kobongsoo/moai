import os
import random
import numpy as np
from typing import Dict, List, Optional
import time

class Quiz_Callback_Template:
   
    def __init__(self, quiz_max_num:int=3):
        self.quiz_max_num = quiz_max_num # 퀴즈 최대 계수
        return
    
    def __del__(self):
        return
    #---------------------------------------------------------------------------------            
    #아래 [퀴즈시작..] 누르면 퀴즈를 시작합니다.
    #총 {3}문제 입니다. 문제를 잘 읽고 정답 번호를 눌러주세요.
    #[퀴즈시작..]
    # quizzes = [{'query': 문제, 'answer': 정답번호, 'info': 설명}]
    #---------------------------------------------------------------------------------      
    def quiz_start(self, quiz_num:int, el_time:str=''):
        assert quiz_num > 0, f'quiz_num is len < 0'
        text:str = f'time:{el_time}\n아래 [퀴즈시작..] 누르면 퀴즈를 시작합니다.\n총{quiz_num}문제입니다.\n문제를 잘 읽고 정답 번호를 눌러주세요'
        template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                            "text": text
                            }
                        }
                    ],
                    "quickReplies": [
                        {
                            "action": "message",
                            "label": "퀴즈시작..",
                            "messageText": '?퀴즈시작..',
                        }
                    ]
                }
            }

        return template
    #--------------------------------------------------------------------------------- 
    #문제1
    #Q: 경주의 대표적인 관광 명소로서, 가을에는 단풍으로 유명한 곳은 어디일까요?
    #1.첨성대
    #2.불국사
    #3.대릉원
    #4.동궁과 월지
    #
    #[1],[2],[3],[4]
    # quiz_query:dict = {'query':문제}
    #--------------------------------------------------------------------------------- 
    def quiz_question(self, quiz_query:dict):
        assert quiz_query, f'quiz_query is empty'
        query = quiz_query['query']
        assert query, f'quiz_query is empty'
        
        text:str = f'Q:{query}'
        template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                            "text": text
                            }
                        }
                    ],
                    "quickReplies": [
                        {
                            "action": "message",
                            "label": "1번",
                            "messageText": '1번',
                        },
                        {
                            "action": "message",
                            "label": "2번",
                            "messageText": '2번',
                        },
                        {
                            "action": "message",
                            "label": "3번",
                            "messageText": '3번',
                        }
                    ]
                }
            }

        return template
    #--------------------------------------------------------------------------------- 
    #O 정답입니다.^^
    #정답은 1번 입니다.
    #[설명]첨성대는 가을에는 단풍으로 유명한 곳으로, 경주의 전형적인 관광 명소입니다.
    #>>총 1문제중 0문제를 맞추셨습니다.
    #[다음문제..] [이제퀴즈그만..]
    #--------------
    #X 틀리셨네요.^^; 
    #정답은 1번 입니다.
    #[설명]첨성대는 가을에는 단풍으로 유명한 곳으로, 경주의 전형적인 관광 명소입니다.
    #>>총 1문제중 0문제를 맞추셨습니다.
    #[다음문제..] [이제퀴즈그만..]
    # quiz_answer:dict = {'answer':정답, 'info': 설명, 'user_answer': 사용자가 선택한 정답}
    #--------------------------------------------------------------------------------- 
    def quiz_answer_info(self, quiz_num:int, quiz_count:int, quiz_answer:dict):
        assert quiz_answer, f'quiz_answer is empty'

        user_answer = quiz_answer['user_answer']
        answer = quiz_answer['answer']
        info = quiz_answer['info']
        
        assert user_answer, f'user_answer is empty'
        assert answer, f'answer is empty'

        if user_answer[0] == answer[0]:
            text = f'⭕️ {answer} 정답 입니다.\n\n[설명] {info}'
        else:
            text = f'❌ 틀리셨네요. 정답은 {answer} 입니다.\n\n[설명] {info}'
            
        template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                            "text": text
                            }
                        }
                    ]
                }
            }

        if quiz_count < quiz_num:
            template["template"]["quickReplies"] = [
                {
                    "action": "message",
                    "label": "다음문제..",
                    "messageText": '?다음문제..'
                },
                {
                    "action": "message",
                    "label": "이제퀴즈그만..",
                    "messageText": '?이제퀴즈그만..'
                }
            ]
        else:
            template["template"]["quickReplies"] = [
                {
                    "action": "message",
                    "label": "돌발퀴즈 다시하기....",
                    "messageText": '?돌발퀴즈..'
                }
            ]
            
        return template    
    #---------------------------------------------------------------------------------  
    # 심플 text 템플릿 
    def quiz_error(self, text:str, quick:dict={}, usercallback:bool=False):
        template = {
                "version": "2.0",
                "useCallback": usercallback,
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": text
                            }
                        }
                    ]
                }
            }

        if len(quick):
            if quick['label'] and quick['message']:
                template["template"]["quickReplies"] = [
                    {
                        "action": "message",
                        "label": quick['label'],
                        "messageText": quick['message']
                    }
                ]
        
        return template
        
        