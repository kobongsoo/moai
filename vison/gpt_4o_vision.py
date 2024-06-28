import os
import sys
import time
import requests
from io import BytesIO
import uuid
import datetime
import json
import base64
from PIL import Image

class GPT_4O_VISION:
    def __init__(self, open_api_key:str):
        self.open_api_key = open_api_key
        return
        
    def __del__(self):
        return

    #------------------------------------------------------------------
    # url 이미지 다운로드 후 파일 사이즈 512*512로 줄여서 저장
    # => 출력 {'credits_left': 2440, 'period': 'month', 'monthly_limit': 2500, 'monthly_usage': 60}
    # -in : url = '??'
    # -in : max_size : 변경할파일사이즈
    # -out: status : 0=성공, 그외=실패
    # -out: save_path : 저장된 경로
    #------------------------------------------------------------------
    def download_and_save_image(self, url:str, max_size=(512, 512)):

        status:int = 0
        
        # 랜덤 파일 이름 생성 (downloads/{랜덤}_{날짜}.jpg)
        random_filename = f"{uuid.uuid4().hex}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        save_path = f"downloads/{random_filename}"
       
        # downloads 폴더 없으면 생성
        os.makedirs("downloads", exist_ok=True)
        
        # 이미지 다운로드
        response = requests.get(url)
        if response.status_code == 200:
            # 이미지 열기
            img = Image.open(BytesIO(response.content))

            # [bong][2024-06-28] 노래만들기 할때 .PNG 파일 업로드 하면 에러남.
            # => PNG 파일은 투명도를 포함할 수 있는 RGBA 모드를 사용할 수 있는데, 그러나 JPEG는 투명도를 지원하지 않기 때문에 에러남.
            # => 따라서 PNG 파일을 JPEG로 변환시 투명 부분을 흰색으로 처리함.
            if img.mode == 'RGBA':
                # 흰색 배경의 새로운 이미지 생성
                background = Image.new("RGB", img.size, (255, 255, 255))
                # 기존 이미지를 배경 이미지에 덮어쓰기
                background.paste(img, (0, 0), img)
                img = background
            
            # 이미지 크기 확인 및 조정
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size)
    
            # JPG 형식으로 저장
            img.save(save_path, "JPEG")
            print(f"이미지가 성공적으로 저장되었습니다: {save_path}")
        else:
            print(f"이미지 다운로드 실패. 상태 코드: {response.status_code}")
            status = response.status_code
    
        return status, save_path

    #------------------------------------------------------------------
    #  이미지를 utf-8 포멧으로 읽어오는 함수
    #------------------------------------------------------------------
    def encode_image(self, image_path:str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    #------------------------------------------------------------------
    #  openai vision으로 이미지 의미를 얻어옴
    # => 모델은 gpt-4o 이
    # 출처 : https://platform.openai.com/docs/guides/vision
    # -in : save_image_path = 로컬이미지경로
    # -in : query : 쿼리
    # -out: status : 0=성공, 그외=실패
    # -out: save_path : 저장된 경로
    #------------------------------------------------------------------
    def get_image_info(self, save_image_path:str, query:str):
        assert save_image_path, f'save_image_path is empty!'
        assert query, f'query is empty!'
        
        start_time = time.time()
        
        # Path to your image
        image_path = save_image_path
        
        # Getting the base64 string
        base64_image = self.encode_image(image_path)
        
        headers = {
          "Content-Type": "application/json",
          "Authorization": f"Bearer {self.open_api_key}"
        }
        
        payload = {
          "model": "gpt-4o",
          "messages": [
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": query
                },
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                  }
                }
              ]
            }
          ],
          "max_tokens": 300
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        # 소요된 시간을 계산합니다.
        end_time = time.time()
        elapsed_time = "{:.2f}".format(end_time - start_time)
        print(f'time:{elapsed_time}')

        res = response.json()
        content = res['choices'][0]['message']['content']
        return content
  
        

    
            

        
        
