import os
import random
import numpy as np
from typing import Dict, List, Optional
import time

class Callback_Template:
    #---------------------------------------------------------------------------------    
    def __init__(self, api_server_url:str, es_index_name:str, qmethod:str):
        assert api_server_url, f'api_server_url is empty'
        assert es_index_name, f'es_index_name is empty'
        assert qmethod > -1, f'qmethod is wrong'

        self.api_server_url = api_server_url
        self.es_index_name = es_index_name
        self.qmethod = qmethod
        self.QUIZ_MAX_LEN = 100   # 숫자 이상인 경우에만 '돌발퀴즈..' 메뉴 보임
    #---------------------------------------------------------------------------------        
    def __del__(self):
        return
    
    #---------------------------------------------------------------------------------           
    # ElasticSearch소숫점 score-> 백분율
    def get_es_format_score(self, score:float)->str:
        formatted_score = "100"
        if score < 2.0:
            formatted_score = "{:.0f}".format((score-1)*100)
        return formatted_score
    #---------------------------------------------------------------------------------            
    # 회사본문검색 
    def template_0(self, query:str, response:str, elapsed_time:str=""):
        assert query, f'query is empty'
        assert response, f'response is empty'

        # weburl = '10.10.4.10:9000/es/qaindex/docs?query='회사창립일은언제?'&search_size=3&qmethod=2&show=1
        weblinkurl = f"{self.api_server_url}/es/{self.es_index_name}/docs?query={query}&search_size=4&qmethod={self.qmethod}&show=1"
        
        template = {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "textCard": {
                                    "title": '📃' + query,
                                    "description": '(time:' + str(elapsed_time) + ')\n' + response,
                                    "buttons": [
                                        {
                                            "action": "webLink",
                                            "label": "내용보기",
                                            "webLinkUrl": weblinkurl
                                        }
                                    ]
                                }
                            }
                        ],
                        "quickReplies": [
                            {
                                "action": "message",
                                "label": "다시검색..",
                                "messageText": '?'+query
                            }
                        ]
                    }
                }

        if len(response) > self.QUIZ_MAX_LEN:
            template['template']['quickReplies'].append(
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            )
        return template
    #---------------------------------------------------------------------------------        
    # 웹검색     
    def template_1(self, query:str, response:str, s_best_contexts:list, elapsed_time:str=""):
        assert query, f'query is empty'
        assert response, f'response is empty'
    
        template = {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "textCard": {
                                    "title": '🌏' + query,
                                    "description": '(time:' + str(elapsed_time) + ')\n' + response,
                                    "buttons": [
                                        {
                                            "action": "webLink",
                                            "label": f"{s_best_contexts[i]['title'][:12]}.." if len(s_best_contexts[i]['title']) > 12 else f"{s_best_contexts[i]['title']}",
                                            "webLinkUrl": s_best_contexts[i]['link']
                                        } for i in range(min(3, len(s_best_contexts)))
                                    ]
                                }
                            }
                        ],
                        "quickReplies": [
                            {
                                "action": "message",
                                "label": "다시검색..",
                                "messageText": '?'+query
                            }
                        ]
                    }
                }
        
        if len(response) > self.QUIZ_MAX_LEN:
            template['template']['quickReplies'].append(
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            )
    
        return template
    #---------------------------------------------------------------------------------    
    # 채팅    
    def template_2(self, query:str, response:str, elapsed_time:str=""):
    
        assert query, f'query is empty'
        assert response, f'response is empty'
    
        if len(response) > 330: # 응답 길이가 너무 크면 simpletext로 처리함
            text = f"🤖{query}\n\n(time:{str(elapsed_time)})\n{response}"                
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
                            "label": "다시질문..",
                            "messageText": '?' + query,
                        },
                        {
                            "action": "message",
                            "label": "새로운대화시작.",
                            "messageText": '?새로운대화시작.'         # [bong][2023-12-11] 채팅모드이면 [새로운대화시작.] 추가함.   
                        }
                    ]
                }
            }
        else:   
            template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "textCard": {
                                "title": '🤖' + query,
                                "description": '(time:' + str(elapsed_time) + ')\n' + response
                            }
                        }
                    ],
                    "quickReplies": [
                        {
                            "action": "message",
                            "label": "다시질문..",
                                    "messageText": '?'+query
                        },
                        {
                            "action": "message",
                            "label": "새로운대화시작.",
                            "messageText": '?새로운대화시작.'         # [bong][2023-12-11] 채팅모드이면 [새로운대화시작.] 추가함.   
                        }
                    ]
                }
            } 

        if len(response) > self.QUIZ_MAX_LEN:
            template['template']['quickReplies'].append(
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            )
    
        return template
    #---------------------------------------------------------------------------------    
    # URL 요약    
    def template_5(self, query:str, response:str, elapsed_time:str=""):
        assert query, f'query is empty'
        assert response, f'response is empty'
     
        if len(response) > 330: # 응답 길이가 너무 크면 simpletext로 처리함          
            text = f"💫{query}\n\n(time:{str(elapsed_time)})\n{response}"
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
                            "label": "다시요약..",
                            "messageText": '?'+query
                        }
                    ]
                }
            }
        else:   
            template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "textCard": {
                                "title": '💫' + query,
                                "description": '(time:' + str(elapsed_time) + ')\n' + response
                            }
                        }
                    ],
                    "quickReplies": [
                        {
                            "action": "message",
                            "label": "다시요약..",
                            "messageText": '?'+query
                        }
                    ]
                }
            }

        if len(response) > self.QUIZ_MAX_LEN:
            template['template']['quickReplies'].append(
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            )
    
        return template
    #---------------------------------------------------------------------------------        
    #이미지 OCR  
    def template_6(self, query:str, response:str, vision_error:int, vision_url:str, elapsed_time:str=""):
    
        assert query, f'query is empty'
        assert response, f'response is empty'
        
        text = f"📷{query}\n\n(time:{str(elapsed_time)})\n{response}"

        if len(response) > self.QUIZ_MAX_LEN and vision_error==0: # 40글자보다는 커야 이미지 내용 요약 처리함.
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
                            "label": "이미지내용요약..",
                            "messageText": '!'+response
                        }
                    ]
                }
            }  
        elif vision_error != 0:
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
                            "label": "📷글자검출 다시하기..",
                            "messageText": '@'+vision_url
                        }
                    ]
                }
            }  
        else:
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

        if len(response) > self.QUIZ_MAX_LEN:
            template['template']['quickReplies'].append(
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            )
             
        return template
    #---------------------------------------------------------------------------------    
    # 이미지OCR 내용 요약(user_mode==7) 인 경우   
    def template_7(self, query:str, response:str, elapsed_time:str=""):
        assert query, f'query is empty'
        assert response, f'response is empty'
         
        if len(response) > 330: # 응답 길이가 너무 크면 simpletext로 처리함
            text = f"{query}\n\n(time:{str(elapsed_time)})\n{response}"                
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
        else: 
            template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "textCard": {
                                "title": query,
                                "description": '(time:' + str(elapsed_time) + ')\n' + response
                            }
                        }
                    ]
                }
            }

        if len(response) > self.QUIZ_MAX_LEN:
            template["template"]["quickReplies"] = [
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            ]
        
        return template
    #---------------------------------------------------------------------------------    
    # 돌발퀴즈인 경우
    def template_8(self, query:str, response:str, elapsed_time:str=""):
        assert query, f'query is empty'
        assert response, f'response is empty'
         
        if len(response) > 330: # 응답 길이가 너무 크면 simpletext로 처리함
            text = f"{query}\n\n(time:{str(elapsed_time)})\n{response}"                
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
        else: 
            template = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "textCard": {
                                "title": query,
                                "description": '(time:' + str(elapsed_time) + ')\n' + response
                            }
                        }
                    ]
                }
            }

        if len(response) > self.QUIZ_MAX_LEN:
            template["template"]["quickReplies"] = [
                {
                    "action": "message",
                    "label": "돌발퀴즈..",
                    "messageText": '?돌발퀴즈..'
                }
            ]
            
        return template
    #---------------------------------------------------------------------------------
    # 본문검색 클릭시 
    def searchdoc(self):
        
        title = "📃본문검색\n질문을 하면 회사본문내용를🔍검색해서 모아이가 답을 합니다."
        descript = '''지금은 모코엠시스 2023년 '회사규정'과 '회사소개' 관련만🔍검색할 수 있습니다.(업데이트 예정..)\n\n[내용보기]를 누르면 검색한 💬본문내용을 볼 수 있습니다.
        '''
        
        template = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                    "basicCard": {
                        "title": title,
                        "description": descript,
                        "thumbnail": {
                            "imageUrl": "http://k.kakaocdn.net/dn/eLnYje/btsA5fPdyHO/fOkPDdHMY6616CNYFiHNkK/2x1.jpg"
                        },
                        "buttons": [
                        {
                          "action":  "message",
                          "label": "출장시 숙박비는 얼마?",
                          "messageText": "출장시 숙박비는 얼마?"
                        },
                        {
                          "action":  "message",
                          "label": "야근 식대는 얼마?",
                          "messageText": "야근 식대는 얼마?"
                        }
                      ]
                     }
                    }
                  ]
               }
            }
    
        return template
    #---------------------------------------------------------------------------------
    # 웹 클릭시
    def searchweb(self):
        
    # http://k.kakaocdn.net/dn/bUP0MS/btsA7RAx01M/sSR0gN6O0kzXN1l66pYvMk/2x1.jpg => 메인
       # http://k.kakaocdn.net/dn/nm41W/btsA9g0UbzW/Fvz12wrGK2duYyLCww2o21/2x1.jpg => URL 입력 요약
       # http://k.kakaocdn.net/dn/eLnYje/btsA5fPdyHO/fOkPDdHMY6616CNYFiHNkK/2x1.jpg => 회사본문검색
       # http://k.kakaocdn.net/dn/bqkjxi/btsA9V3gT5i/JRbnnpxeoxG6ok4H3rX9Tk/2x1.jpg => 웹검색
       # http://k.kakaocdn.net/dn/bbRJLT/btsBb5xrDyJ/cOKisJNsExLV77kHBTOTHk/2x1.jpg => AI응답모드
       # http://k.kakaocdn.net/dn/lGVgi/btsA5hTJGUL/tUo5HnahK3aMGO9XJ49t21/2x1.jpg => 설정
       # http://k.kakaocdn.net/dn/bRDZcJ/btsA9TqM29J/N79nlPR6shWiNuOycmsG1k/2x1.jpg=>피드벡
        title = "🌐웹검색\n질문을 하면 네이버,구글🔍검색해서 모아이가 답을 합니다."
        descript = "답변은 최대⏰30초 걸릴 수 있고,종종 엉뚱한 답변도 합니다.\n\n버튼을 클릭하면 검색한 🌐URL로 연결됩니다."
        template = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                    "basicCard": {
                        "title": title,
                        "description": descript,
                        "thumbnail": {
                            "imageUrl": "http://k.kakaocdn.net/dn/bqkjxi/btsA9V3gT5i/JRbnnpxeoxG6ok4H3rX9Tk/2x1.jpg"
                        },
                        "buttons": [
                        {
                          "action":  "message",
                          "label": "제주도 봄 여행코스 추천",
                          "messageText": "제주도 봄 여행코스 추천"
                        },
                        {
                          "action":  "message",
                          "label": "2023년 한국야구 우승팀은?",
                          "messageText": "2023년 한국야구 우승팀은?"
                        }
                      ]
                     }
                    }
                  ]
               }
            }
    
        return template
    #---------------------------------------------------------------------------------
    # 채팅 클릭시
    def chatting(self):
        
        title = "🤖채팅하기\n새로운 대화를 시작합니다.\n모아이와 질문을 주고받으면서 채팅하세요."
        descript = '''질문을 이어가면서 대화할 수 있습니다.
        '''
        template = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                    "basicCard": {
                        "title": title,
                        "description": descript,
                        "thumbnail": {
                            "imageUrl": "http://k.kakaocdn.net/dn/bbRJLT/btsBb5xrDyJ/cOKisJNsExLV77kHBTOTHk/2x1.jpg"
                        },
                        "buttons": [
                        {
                          "action":  "message",
                          "label": "봄 여행지 추천 목록",
                          "messageText": "봄 여행지 추천 목록"
                        },
                        {
                          "action":  "message",
                          "label": "목록들을 설명해줘",
                          "messageText": "목록들을 설명해줘"
                        }
                      ]
                     }
                    }
                  ]
               }
            }
            
    
        return template
    #--------------------------------------------------------------------------------- 
    # 설정
    def setting(self, linkurl:str, descript:str):
 
        template = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                    "basicCard": {
                        "title": "사용자정보 & 설정",
                        "description": descript,
                        "thumbnail": {
                            "imageUrl": "http://k.kakaocdn.net/dn/lGVgi/btsA5hTJGUL/tUo5HnahK3aMGO9XJ49t21/2x1.jpg"
                        },
                        "buttons": [
                        {
                            "action": "webLink",
                            "label": "⚙️설정하기",
                            "webLinkUrl": linkurl
                        }
                      ]
                     }
                    }
                  ]
               }
            }

        return template
    #---------------------------------------------------------------------------------
    # 이전 대화 
    def pre_answer(self, query:str, prequery:str, prequery_response:str, user_mode:int, prequery_score:float):
         # 1.80 이상일때만 이전 답변 보여줌.
        if prequery_score >= 1.80:  
            label_str:str = "다시검색.."
            if user_mode == 0:
                query1 = f'📃{query}'                   
            elif user_mode == 1:
                query1 = f'🌐{query}'
            else:
                query1 = f'🤖{query}'
                label_str = "다시질문.."
                        
            # 정확도 스코어 구함
            format_prequery_score = self.get_es_format_score(prequery_score)
            pre_descript =   f'💬예전 질문과 답변입니다. (유사도:{format_prequery_score}%)\nQ:{prequery}\n{prequery_response}'  
            pre_template = {
                "version": "2.0",
                "template": {
                    "outputs": [],
                    "quickReplies": [
                        {
                            "action": "message",
                            "label": label_str,
                            "messageText": '?'+query
                        }
                        ]
                    }
                }
            if len(pre_descript) > 330:
                pre_template["template"]["outputs"].append({
                    "simpleText": {
                        "text": f'{query1}\n\n{pre_descript}'
                    }
                })
            else:
                pre_template["template"]["outputs"].append({
                    "textCard": {
                        "title": query1,
                        "description": pre_descript
                    }
                })

            return pre_template
        else:
            return ""
            
    #---------------------------------------------------------------------------------  
    # 심플 text 템플릿 
    def simpletext_template(self, text:str, usercallback:bool=False):
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
        
        return template

    #---------------------------------------------------------------------------------  
    def usecallback_template(self, text:str, usercallback:bool=False):
        template = {
            "version": "2.0",
            "useCallback": usercallback,
            "data": {
                "text" : text
            }
        }

        return template
    #---------------------------------------------------------------------------------  
   
    
        
    
