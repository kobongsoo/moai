import requests
import json
import urllib

class KarloAPI:
    
    def __init__(self, rest_api_key:str):
        assert rest_api_key, f'res_api_key is empty'
        self.rest_api_key = rest_api_key
        return

    def __del__(self):
        return

    def text2image(self, prompt:str, negative_prompt:str, width:int=384, height:int=384, image_format:str='jpeg'):
        r = requests.post(
            'https://api.kakaobrain.com/v2/inference/karlo/t2i',
            json = {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'width' : width,
                'height' : height,
                'image_format': image_format
            },
            headers = {
                'Authorization': f'KakaoAK {self.rest_api_key}',
                'Content-Type': 'application/json'
            }
        )
        # 응답 JSON 형식으로 변환
        response = json.loads(r.content)
        return response
    