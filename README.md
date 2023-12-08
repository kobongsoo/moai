# moai
<br>모아이(moai)는 이스타섬이 얼굴석상을 말하며, mo+AI 합쳐서 moai 입니다.
<br>모아이는 카카오톡에서 사용할 수 있는 채팅 및 검색 AI 로써 카카오톡에서 아래 채널을 등록하시면 사용할수 있습니다.
- 카카오톡 채널 : http://pf.kakao.com/_tdLxjG/chat
## 주요기능
1. 질문을 하면 이전 검색 및 질문 해던 내용에서 **유사한 질문과 답변**을 보여줍니다.
2. **URL을 입력하면 내용을 요약**해 줍니다.
3. **이미지를 입력하면 글자를 추출**해 내용을 보여주거나 요약 해 줍니다.
4. 네이버나 구글을 선택해서 **웹검색 내용을 요약**해 보여 줍니다.
5. **회사문서내용을 본문검색** 할수 있습니다.
6. **AI와 질문을 이어가면서 채팅**을 할 수 있습니다.

## 서비스 구축 방법
### 1. 외부 URL 
- 카카오톡 연동을 위해 외부에서 내부 접근가능한 URL이 필요한데, 여기서는 ngrok 을 이용해서 만든다. 회원가입후 Your Authtoken  획득 후, ngrok.exe 다운로드 실행하면 됨.
'''
ngrok config add-authtoken xxxxxxxxxxxxxxxxxx
ngrok http 9000
'''
  <br> 참고 : https://ngrok.com/
  
### 2. 카카오톡 채널과 챗봇 개설 & 연동
- 카카오톡 비지니스에 가입해서 채널과 챗봇을 만듬.
<br> 참조: https://blog.naver.com/michaelchae/222640935084
- 콜백 신청 : 챗봇 > 설정 > AI 챗봇 관리 에서 AI 챗봇을 신청(1일 걸림)
<img width="441" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/7c2a5530-2404-431e-877e-9a5ac6d9fa7b">

- 챗봇 > 풀백 스킬 등록 : URL은 "https:/{ngrokurl}/chatbot3" 식으로 등록.
<img width="518" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/fb35a1b1-444a-4be5-95bd-474f966599b0">
  
- 챗봇 > 시나리오 > 풀백블록에 위 플백 스킬 연동. 이후 [...] 눌러서 Callback 설정 하고 아래처럼 입력.
<img width="420" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/2e1dfae3-33f7-4c39-a412-cc6af705ef85">

- 챗봇 > 기타 스킬 등록 : 아랙 5개 스킬 등록
```
본문검색스킬 : https://{ngrokurl}/searchdoc 
웹문서스킬 : https://{ngrokurl}/searchweb
채팅스킬 : https://{ngrokurl}/searchai
설명스킬 : https://{ngrokurlL}/info
설정스킬 : https://{ngrokurl}/setting
```
- 챗봇 > 시나리오 : 3개 블록 생성 하고 각 스킬을 연결한다.
  <br> 본문검색블록 : 본문검색스킬 연결, 웹문서검색블록: 웹문서검색 스킬 연결, 채팅문서블 : 채팅스킬 연결
- 챗봇 > 시나리오 설정 클릭후 커스텀메뉴 만들고, '채팅하기', '본문검색', '웹검색' 버튼 추가함.
<img width="402" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/ba298139-148a-4531-88e2-9e3bd011ae38">

- 챗봇 > 설정을 눌러서 카카오톡 채널 연결에서 챗봇과 채널 연결한다.
- 챗봇 > 배포를 눌러서 배포 하면, 이제 카카오톡에서 생성한 채널로 들어가면 된다.

### 3. 모아이 서버 실행
- 모아이는 docker 이미지로 구성되어 있으므로, 아래처럼 docker compose로 실행하면 됨.
#### 1) 실행할 경로에 moai_log, moai_data, moai_esdata 폴더 생성.
- data 폴더에 있는 kakao.db, mpower10u_128d_10.json, settings_128.yaml 를 moai_data 폴더에 복사
  
#### 2) settings_128.yaml 파일 수정
- settings_128.yml 파일을 열고 아래와 같은 값들을 수정해야 함.
- 각 key나 id는 회원가입후 얻어야 함. 네이버 검색 api 는 1일/25,000 , 구굴 검색 1일/10,000, openaiapi는 회원가입시 5$를 줌.
```
ES_URL: elasticsearch 서버 주소 : docker 구동하는 시스템에 ip
API_SERVER_URL: ngrok url

GPT_TOKEN:  openai api key => https://antilibrary.org/2760

NAVER_CLIENT_ID: 네이버 검색 id : https://developers.naver.com/main/
NAVER_CLINET_SECRET:  네이버 검색 secret : https://developers.naver.com/main/

GOOGLE_API_KEY: 구글 검색을 위한 api key => 참고: https://programmablesearchengine.google.com/controlpanel/all
GOOGLE_SEARCH_ENGINE_ID: 구글 검색 엔진 id
```
#### 3) Google Cloud Vision API 키 발급
- https://yunwoong.tistory.com/148 참고하여, xxx.json 파일 발급 하여 vison-ocr.json 으로 이름 변경 후 moai_data 폴더에 복사.(이미지 글자 추출 용도)

#### 4) 아래처럼 moai-compose.yml 을 만들고 compose로 실행
- docker compose -p m -f ./moai-compose.yml up -d
```
# moai-compose.yml file
version: '1.0'

services:
  elasticsearch:
    image: bong9431/elasticsearch:7.17.13.1
    restart: always
    environment:
      - discovery.type=single-node
    ports: 
      - 9200:9200
      - 9300:9300
    networks:
      - es_network
    volumes:
      - ./moai_es_data:/usr/share/elasticsearch/data
    
  kibana:
    image: kibana:7.17.13
    restart: always
    depends_on:
        - elasticsearch
    ports:
      - 5601:5601
    networks:
      - es_network

  moai:
      image: bong9431/moai:0.9
      restart: always
      depends_on:
        - elasticsearch
      ports:
        - 9000:9000
        - 9999:9999
      networks:
        - es_network
      volumes:
        - ./moai_log:/moai/log
        - ./moai_data:/moai/data

networks:
  es_network:

```
## 참고소스
|명칭|설명|참고|
|:----------------|:---------------------------------------------------------|--------|
|[documet_embed](https://github.com/kobongsoo/moai/blob/master/documet_embed.ipynb)|문서들을 elasticsearch로 임베딩 하는 코드||
|[google_search](https://github.com/kobongsoo/moai/blob/master/google_search.ipynb)|구글 검색 예제|1일 10,000건 무료|
|[google_vison_ocr](https://github.com/kobongsoo/moai/blob/master/google_vison_ocr.ipynb)|구글 비전 OCR 예제|1달 10,000건 무료, 10,000건당 1.5$|
|[googletrans_test](https://github.com/kobongsoo/moai/blob/master/googletrans_test.ipynb)|구글 번역 예제|무료:번역 질이 좀 떨어짐|
|[gpt_test](https://github.com/kobongsoo/moai/blob/master/gpt_test.ipynb)|gpt 테스트 예제||
|[naver_search_test](https://github.com/kobongsoo/moai/blob/master/naver_search_test.ipynb)|네이버 검색 예제|1일 25,000건|
|[papago_test](https://github.com/kobongsoo/moai/blob/master/papago_test.ipynb)|네이버 파파고 테스트 예제|1일 10,000자|
|[sqllitedb_test](https://github.com/kobongsoo/moai/blob/master/sqllitedb_test.ipynb)|sqlite 테스트 예제||
|[webscraping_test](https://github.com/kobongsoo/moai/blob/master/webscraping_test.ipynb)|웹스크래핑 예제||



