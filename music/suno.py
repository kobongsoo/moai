import os
import sys
import time
import requests
from io import BytesIO
import uuid
import datetime
import json

class SUNO:
    def __init__(self):
        return
        
    def __del__(self):
        return

    #------------------------------------------------------------------
    # 사용량 얻기 : GET api/get_limit
    # => 출력 {'credits_left': 2440, 'period': 'month', 'monthly_limit': 2500, 'monthly_usage': 60}
    # -in : host = 'http://192.168.0.61:3000'
    # -out: status:int=상태값(0=성공, 그외=실패)
    # -out: res:str={'credits_left': 2440, 'period': 'month', 'monthly_limit': 2500, 'monthly_usage': 60}, 에러일때는=에러메시지 
    #------------------------------------------------------------------
    def get_limit(self, host:str):
        assert host, f'host is empty'
        
        # URL 설정
        url = f"{host}/api/get_limit"
        
        # GET 요청 보내기
        response = requests.get(url)
        
        # 응답 확인
        status:int = 0
        if response.status_code == 200:
            print("*사용량 얻기 성공.")
            print("*응답:", response.json())
            res = response.json()
        else:
            print("*사용량 얻기 실패. 상태 코드:", response.status_code)
            print("*응답:", response.text)
            res = response.text
            status = response.status_code

        return status, res

    #------------------------------------------------------------------
    # 음악 생성 => 음악 id가 생성됨=> 나중에 음악 id를 입력해서 실제 url 얻어와야 함.
    # -in : prompt = '벗꼿이 휘날리는 조용한 시골길 거리'
    # -in : host = 'http://192.168.0.61:3000'
    # -out: status:int = 상태값(0=성공, 그외=실패)
    # -out: ids:list = 생성된 음악id 2개, 에러일때는 ids[0]=에러메시지 
    #------------------------------------------------------------------
    def create(self, prompt:str, host:str):
        
        assert host, f'host is empty'
        assert prompt, f'prompt is empty'

        start_time = time.time()
        
        # URL 설정
        url = f"{host}/api/generate"

        if len(prompt) > 200:
            prompt = prompt[:199]
            
        # 요청 데이터 설정
        data={
          "prompt": prompt,
          "make_instrumental": False,
          "wait_audio": False
        }
        
        # 헤더 설정 (JSON 데이터를 보내므로 Content-Type을 application/json으로 설정)
        headers = {
            "Content-Type": "application/json"
        }
        
        # POST 요청 보내기
        response = requests.post(url, data=json.dumps(data), headers=headers)
        
        # 소요된 시간을 계산합니다.
        end_time = time.time()
        elapsed_time = "{:.2f}".format(end_time - start_time)
        print(f'*time:{elapsed_time}')
        
        # 응답 확인
        status:int = 0
        ids:list = []
        if response.status_code == 200:
            print("*음악생성 성공")
            print("*응답:", response.json())

            # response에서 id만 뽑아냄 => id는 2개 만들어짐.
            suno_res = response.json()
            
            for suno in suno_res:
                id = suno['id']
                if id:
                    ids.append(id)

        else:
            print("*음악생성 실패. 상태 코드:", response.status_code)
            print("*응답:", response.text)
            status = response.status_code
            ids.append(response.text)

        return status, ids

    #------------------------------------------------------------------
    # 음악 url 얻기 => 음악 id가 입력후 음악 mp3, mp4 url 얻기
    # -in : ids:list = 생성된 음악id 2개
    # -in : host = 'http://192.168.0.61:3000'
    # -in : max_retries = 최대 반복횟수
    # -out: status:int = 상태값(0=성공, 그외=실패)
    # -out: datalist:list = [{'id': 'efd952d7-6d00-4ce6-b5a8-36d2e59996fb', 'title': '숲속 여행', 'image_url': 'https://cdn1.suno.ai/image_efd952d7-6d00-4ce6-b5a8-36d2e59996fb.png', 'lyric': '[Verse]\n여름날 숲속에서\n우리 사랑해요\n바람 불어오는 길\n행복 가득해요\n[Verse 2]\n푸른 나무 사이로\n햇살 비춰줄 때\n웃음소리 가득한\n우리 가족 함께해\n[Chorus]\n숲속으로 떠나요\n다같이 손잡고\n추억을 만들어요\n여름날 속으로\n[Bridge]\n숲속 향기 맡으며\n이 순간 느끼며\n모든 걱정 날려요\n여름날의 행복\n[Verse 3]\n파란 하늘 아래서\n마음 편안해요\n사랑하는 가족과\n함께라서 좋아요\n[Chorus]\n숲속으로 떠나요\n다같이 손잡고\n추억을 만들어요\n여름날 속으로', 'audio_url': 'https://cdn1.suno.ai/efd952d7-6d00-4ce6-b5a8-36d2e59996fb.mp3', 'video_url': 'https://cdn1.suno.ai/efd952d7-6d00-4ce6-b5a8-36d2e59996fb.mp4', 'created_at': '2024-06-11T01:32:55.562Z', 'model_name': 'chirp-v3.5', 'status': 'complete', 'gpt_description_prompt': '여름에 숲속으로 사랑하는 가족들과 여행을 떠나자.', 'prompt': '[Verse]\n여름날 숲속에서\n우리 사랑해요\n바람 불어오는 길\n행복 가득해요\n\n[Verse 2]\n푸른 나무 사이로\n햇살 비춰줄 때\n웃음소리 가득한\n우리 가족 함께해\n\n[Chorus]\n숲속으로 떠나요\n다같이 손잡고\n추억을 만들어요\n여름날 속으로\n\n[Bridge]\n숲속 향기 맡으며\n이 순간 느끼며\n모든 걱정 날려요\n여름날의 행복\n\n[Verse 3]\n파란 하늘 아래서\n마음 편안해요\n사랑하는 가족과\n함께라서 좋아요\n\n[Chorus]\n숲속으로 떠나요\n다같이 손잡고\n추억을 만들어요\n여름날 속으로', 'type': 'gen', 'tags': 'melodic acoustic pop'}]
    #------------------------------------------------------------------
    def getfile_by_ids(self, ids:list, host:str, max_retries:int=20):
        
        assert host, f'host is empty'
        assert len(ids) > 0, f'ids is len < 1'
        assert max_retries > 0, f'max_retries is len < 0'

        start_time = time.time()
        
        # URL 설정
        url = f"{host}/api/get"
        print(f"*url: {url}")
        
        status:int = 0
        datalist:list=[]
        
        for attempt in range(max_retries):
            print(f"*count: {attempt}")
            for id in ids:
                # 쿼리 파라미터
                params = {
                    "ids": id
                }
                
                # GET 요청 보내기
                mp_response = requests.get(url, params=params)
                
                # 응답 코드 확인
                print(f"*Status Code: {mp_response.status_code}")
                print(f"*params: {params}")
                
                # 응답 내용 출력
                if mp_response.status_code == 200:
                    data = mp_response.json()
                    print("Response Content:")
                    print(data)
                    print('*' * 50)  
                    
                    video = data[0]['video_url']
                    audio = data[0]['audio_url']

                    if video and audio: 
                        datalist.append(data[0])
                else:
                    print("Failed to retrieve data")
        
            # video_urls와 audio_urls의 길이 확인
            if len(datalist) > 1:
                break

            if max_retries > 1:
                # 다음 시도를 위해 10초 대기
                time.sleep(10)
        
        if len(datalist) < 2:
            print("Failed to retrieve enough data within the maximum number of attempts.")
            status = 101
        else:
            print("Successfully retrieved the required data.")
            status = 0

        # 소요된 시간을 계산합니다.
        end_time = time.time()
        elapsed_time = "{:.2f}".format(end_time - start_time)
        print(f'*time:{elapsed_time}')
        
        return status, datalist

        

    
            

        
        