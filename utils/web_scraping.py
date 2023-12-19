import re
import chardet
import urllib.request
import requests
import os
from bs4 import BeautifulSoup

# 웹스크래핑 처리
class WebScraping:
    
    def __init__(self, scraping_web_max_len:int=4000):
        assert scraping_web_max_len > 0, f'scraping_web_max_len is < 0'
        scraping_web_max_len = scraping_web_max_len
        return
    
    def __del__(self):
        return
    
    def is_url(self, url:str)->bool:
        assert url, f'url is empty'
        regex = r"(http|https)://(www\.)?" + r"[a-zA-Z0-9-_]+(\.[a-zA-Z0-9-_]+)*(\.[a-zA-Z]{2,})"
        
        match = re.match(regex, url)
        return match is not None
    
    def url_download(self, url:str, filepath:str)->int:
        assert url, f'url is empty'
        assert filepath, f'filepath is empty'
        
        try:
            # 폴더가 없으면 생성
            dir_path = os.path.dirname(filepath)  
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            if self.is_url(url) == False:
                return 1001

            response = urllib.request.urlopen(url)
            file = open(filepath, 'wb') # 파일 객체 열기(pdf 파일은 바이너리 파일이므로 w에 더해 b옵션 추가
            file.write(response.read())  # 연 파일 객체에 다운받은 pdf 파일 바이너리 데이터 기록             
            file.close()                 # 파일 객체 닫기
            #print("pdf 파일 저장 완료")
            return 0
        except Exception as e:
            print(f'url_download=>error:{e}')
            return 1001
        
    def detect_encoding(self, filepath:str):
        assert filepath, f'filepath is empty'
        with open(filepath, 'rb') as f:
            raw_data = f.read()
        detected = chardet.detect(raw_data)
        return detected['encoding']

    def read_file(self, filepath:str):
        try:
            assert filepath, f'filepath is empty'
            encoding = self.detect_encoding(filepath)
            #print(f'encoding:{encoding}\n')
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f'read_file=>error:{e}')
            return ""
        
    # 파일을 열고 읽기 모드로 설정합니다.
    def readlines_file(self, filepath:str, min_len:int=20):
        assert filepath, f'filepath is empty'
        text:str = ''
        try:
            with open(filepath, 'r') as f:
                # 파일의 모든 줄을 읽습니다.
                lines = f.readlines()

            # 줄을 출력합니다.
            for line in lines:
                if len(line) > min_len:
                    text += line

            return text
        except Exception as e:
            print(f'readlines_file=>error:{e}')
            return ""
    
    def scraping_file(self, url:str, filepath:str, min_len:int=100)->str:
        
        context:str = ""
        
        # URL 다운로드
        ret = self.url_download(url=url, filepath=filepath)
        if ret != 0:
            print(f'url_download is fail')
            return ""
        
        # 다운로드한 파일 읽어오기
        text = self.read_file(filepath=filepath)     
        if len(text) < 100:
            return ""
        
        # 스크래핑
        soup = BeautifulSoup(text, 'html.parser')
        findtext = soup.find_all(name='div')
        
        text_list:list = []
        

        if findtext:
            '''
            text = findtext[0].get_text().strip()
               
            text = text.replace('\n', '')
            text = text.replace('\t', '') 
            print(f'{len(text)}:{text}')
            context = text
            '''
                    
            for idx in range(len(findtext)):
                text = findtext[idx].get_text().strip()
                
                text = text.replace('\n', '')
                text = text.replace('\t', '')  
                #print(f'{len(text)}:{text}')
                if len(text) > min_len:   # 글자가 100자 이상긴 경우에만
                    
                    # 중복된 문장 제거
                    if any(pretext in text for pretext in text_list):
                        continue

                    #print(f'{len(text)}:{text}')
                    # 6000 보다 크면 break
                    if len(context) > 6000:
                        break
                        
                    text_list.append(text)
                    context += text+'\n'
       
        # 파일 삭제
        try:
            os.remove(filepath)
        except FileNotFoundError:
            print(f"\scraping_file=>{filepath} 파일이 존재하지 않습니다.")
        except Exception as e:
            print(f"\scraping_file=>파일 삭제 중 오류가 발생했습니다: {e}")
                        
        return context
    
    def scraping(self, url:str, min_len:int=100)->str:
        assert url, f'url is empty'
         
        #response = requests.get(url, headers={'Accept-Charset': 'UTF-8'})
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        findtext = soup.find_all(name='div')
        
        context:str = ""
        text_list:list = []
        if findtext:
            '''
            text = findtext[0].get_text().strip()
               
            text = text.replace('\n', '')
            text = text.replace('\t', '') 
            print(f'{len(text)}:{text}')
            context = text
            '''
                    
            for idx in range(len(findtext)):
                text = findtext[idx].get_text().strip()
                
                text = text.replace('\n', '')
                text = text.replace('\t', '')  
                #print(f'{len(text)}:{text}')
                if len(text) > min_len:   # 글자가 100자 이상긴 경우에만
                    
                    # 중복된 문장 제거
                    if any(pretext in text for pretext in text_list):
                        continue

                    #print(f'{len(text)}:{text}')
                    # 6000 보다 크면 break
                    if len(context) > 6000:
                        break
                        
                    text_list.append(text)
                    context += text+'\n'
                  
        return context

    # url 스크래핑 한후 synap으로 문서내용 추출하는 함수 
    # url: 추출할 url(문서url 혹은 웹페이지), srcfilepath: url 다운로드후 저장할 파일경로, tarfilepath: synap으로 내용 추출후 저장할 파일 경로
    def scraping_web(self, url:str):
        assert url ,f'url is empty'
       
        error:int = 0; text:str = ""
    
        try:
            text = self.scraping(url=url, min_len=20)
            if len(text) > self.scraping_web_max_len:
                text = text[0:self.scraping_web_max_len-1]
        except Exception as e:
            print(f'extract error=>{e}')
            error = 1002    
        return text, error