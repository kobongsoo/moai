# moai
<img width="212" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/b36c2ab1-2723-4bd6-9984-a00693bdc9c4">


<br>모아이(moai)는 이스타섬이 얼굴석상을 말하며, mo+AI 합쳐서 moai 입니다.
<br>모아이는 카카오톡에서 사용할 수 있는 채팅 및 검색 AI 로써 카카오톡에서 아래 채널을 등록하시면 사용할 수 있습니다.
- 카카오톡 채널 : http://pf.kakao.com/_tdLxjG/chat
## 주요기능
1. 질문을 하면 이전 검색 및 질문 해던 내용에서 **유사한 질문과 답변**을 보여줍니다.
2. **URL을 입력하면 내용을 요약**해 줍니다.
3. **이미지를 입력하면 글자를 추출**해 내용을 보여주거나 요약 해 줍니다.
4. 네이버나 구글을 선택해서 **웹검색 내용을 요약**해 보여 줍니다.
5. **회사문서내용을 본문검색** 할수 있습니다.
6. **AI와 질문을 이어가면서 채팅**을 할 수 있습니다.
7. **돌발퀴즈** 도 할 수 있습니다.
8. **Text을 입력해서 이미지를 생성** 할 수도 있습니다.(카카오 karlo api 이용)

[참고] **bert모델은 github에 포함되지 않음**. (kpf-sbert-128d-v1 사용함.)

## 서비스 구축 방법
### 1. 외부 URL 
- 카카오톡 연동을 위해 외부에서 내부 접근가능한 URL이 필요한데, 여기서는 ngrok 을 이용해서 만든다. 회원가입후 Your Authtoken  획득 후, ngrok.exe 다운로드 실행하면 됨.
```
ngrok config add-authtoken xxxxxxxxxxxxxxxxxx
ngrok http 9000
```
  <br> 참고 : https://ngrok.com/
  
### 2. 카카오톡 채널과 챗봇 개설 & 연동
- 카카오톡 비지니스 (https://business.kakao.com/dashboard/) 에 가입해서 채널과 챗봇을 만듬.
<br> 참조: https://blog.naver.com/michaelchae/222640935084
- 콜백 신청 : 챗봇 > 설정 > AI 챗봇 관리 에서 AI 챗봇을 신청(1일 걸림)
<img width="441" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/7c2a5530-2404-431e-877e-9a5ac6d9fa7b">

- 챗봇 > 풀백 스킬 등록 : URL은 "https:/{ngrokurl}/**chatbot3**" 식으로 등록.
<img width="744" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/4a708c4c-baa9-4413-a5b1-372031be2b18">

- 챗봇 > 시나리오 > 백블록에 위 플백 스킬 연동. 이후 [...] 눌러서 Callback 설정 하고 **{{#webhook.text}}** 입력.
<img width="701" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/0f914689-6595-4ed3-a166-33e217cc0251">

<img width="403" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/6f1c0dff-ec27-40ab-8ea4-ec6ff199a97c">

- 챗봇 > 기타 스킬 등록 : 풀백 스킬 등록때 처럼 아래 5개 스킬 등록
```
본문검색스킬 : https://{ngrokurl}/searchdoc
웹문서스킬 : https://{ngrokurl}/searchweb
채팅스킬 : https://{ngrokurl}/searchai
설명스킬 : https://{ngrokurlL}/info
설정스킬 : https://{ngrokurl}/setting
이미지만들기스킬 : https://{ngrokurl}/paint
```
- 챗봇 > 시나리오 : 4개 블록 생성 하고 각 스킬을 연결한다.
```
본문검색블록 <-> 본문검색스킬 연결
웹문서검색블록 <-> 웹문서검색 스킬 연결
채팅문서블록 <-> 채팅스킬 연결
이미지만들기블록 <-> 이미지만들기스킬 연결
```
<img width="711" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/3a58f16d-bba0-4b34-b4b4-d171169e9202">

- 챗봇 > 시나리오 설정, 클릭 후 커스텀메뉴 만들고, '채팅하기', '본문검색', '웹검색' 버튼 추가함.
<img width="407" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/908d86fb-1b3c-4298-b7b8-87f382e4aa39">

- 챗봇 > 설정을 눌러서 카카오톡 채널 연결에서 챗봇과 채널 연결한다.
<img width="633" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/c0733357-6581-4c52-9b29-83a22597cf11">

- 챗봇 > 배포를 눌러서 배포 하면, 이제 카카오톡에서 생성한 채널로 들어가면 된다.
<img width="631" alt="image" src="https://github.com/kobongsoo/moai/assets/93692701/f79d2a3c-ed14-4a3d-bdf6-2f3c1c7b3785">

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

GOOGLE_API_KEY: 구글 검색을 위한 api key => https://www.delftstack.com/ko/howto/python/python-google-search-api/
GOOGLE_SEARCH_ENGINE_ID: 구글 검색 엔진 id => 검색엔진 만들기: https://programmablesearchengine.google.com/controlpanel/all 
```
#### 3) Google Cloud Vision API 키 발급
- https://yunwoong.tistory.com/148 참고하여, xxx.json 파일 발급 하여 vison-ocr.json 으로 이름 변경 후 moai_data 폴더에 복사.(이미지 글자 추출 용도)

#### 4) 아래처럼 moai-compose.yml 을 만들고 compose로 실행
- docker compose -p m -f ./moai-compose.yml up -d
- 참고: [도커허브](https://hub.docker.com/repository/docker/bong9431/moai/general)
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
      image: bong9431/moai:latest
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
## 모아이 코드 수정-1
- 모아이 코드를 수정하려면 여려 패키지를 설치해야 하므로, 여기서는 moai docker 이미지를 실행하고, jupyterlab을 실행해서 수정하는 방법을 설명한다.
#### 1. compose 실행
- 위 moai-compose.yml 를 compose로 데몬(-d) 으로 실행한다.
```
docker compose -p m -f ./moai-compose.yml up -d
```
#### [참고] compose 로 중지
```
docker compose -p m -f ./moai-compose.yml down
```
#### 2. jupyter 실행
- exec로 moai 쉘로 들어가서, sh 로 jupyter을 실행해 준다.
```
docker exec -it m-moai-1 /bin/bash
[root@487150982e6] sh jupyter.sh start
Starting jupyter
jupter started
```
- 실행후, CTRL+ P + Q 눌러서 쉘을 빠져 나온다,

#### 3. jupyter 접속 확인
- localhost:9999 로 접속 확인 해 본다. 토큰은 moai_log 폴더에 jupyter.log 파일을 열어보면 된다.

## 모아이 코드 수정-2
- 여기서는 moai docker 이미지를 jupyterlab 실행할수 있는 이미지로 만들고 수정하는 방법을 설명한다.
#### 1. Dockerfile 생성.
- 아래처럼 Dockerfile을 만들고, docker 이미지를 만든다. 
```
#base image
FROM bong9431/moai:1.4

#metatag
MAINTAINER bong9431
LABEL "title"="moai"

#workdir
WORKDIR /moai

#run
#RUN mkdir /log

#cmd
CMD jupyter lab --ip=0.0.0.0 --port=9999 --allow-root
```
#### 2. Docker 이미지 생성
- 아래처럼 Dockerfile을 실행해서 이미지를 만든다.
```
docker build -t moai-jupyter:1.0 -f ./Dockerfile .
```

#### 3. Docker 이미지 실행
- 9999번 포트 지정해서 docker 이미지 실행. moai 폴더 경로 입력
```
docker run -d --name mj -p 9999:9999 moai-jupyter:1.0
```
#### 4. jupyterlab 접속 확인
- localhost:9999 로 웹에서 접속 확인. token은 아래처럼 확인해서 입력하면됨.
```
docker logs mj

[I 2024-02-15 01:13:49.257 ServerApp] http://4390649f6a60:9999/lab?token=9aa5e9a2b61770179ea8c2080fb0f9ab6f3b84bb754ca185
[I 2024-02-15 01:13:49.257 ServerApp]     http://127.0.0.1:9999/lab?token=9aa5e9a2b61770179ea8c2080fb0f9ab6f3b84bb754ca185
```
#### 5. 이미지 생성
- commit 명령어로 수정 후 새로운 이미지(예: moai-jupyter:1.1) 로 만든다.
```
docker commit mj moai-jupyter:1.1
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
|[parser_test](https://github.com/kobongsoo/moai/blob/master/parser_test.ipynb)|돌발퀴즈 문자열 파싱하는 예제||

## 생성모델 소스
|명칭|설명|참고|
|:----------------|:---------------------------------------------------------|--------|
|[langchain_RAS](https://github.com/kobongsoo/moai/blob/master/model_test/gemma/langchain_RAS.ipynb)|LangChain 프레임워크를 이용한 RAG 및 sLLM 모델 로딩 예시|해당 폴더에 .env파일을 만들고, OPENAI_API_KEY='{API_KEY}',  HUGGINGFACEHUB_API_TOKEN='{API_TOKEN}'식으로 입력해야 함.|
|[gemma_sum_train](https://github.com/kobongsoo/moai/blob/master/model_test/gemma/gemma-2b-it-sum-ko.ipynb)|구글gemma-2b-it 모델을 가지고 요약 데이터 훈련시키는 예제|테스트 소스: [gemma_test](https://github.com/kobongsoo/moai/blob/master/model_test/gemma/gemma_test.ipynb)|
|[gemma_qa_train](https://github.com/kobongsoo/moai/blob/master/model_test/gemma/gemma_train.ipynb)|구글 gemma-2b-it 모델을 가지고 Q&A 데이터 훈련시키는 예제|테스트 소스: [gemma_test2](https://github.com/kobongsoo/moai/blob/master/model_test/gemma/gemma_test2.ipynb)|
|[gemini_test1](https://github.com/kobongsoo/moai/blob/master/model_test/gemini/geminai_test.ipynb)|구글 gemini 모델 Vertex AI API 연동 테스트..**JSON 인증키 파일 발급 필요**|gemini API 연동 샘플 코드들 : [gemini](https://github.com/kobongsoo/moai/tree/master/model_test/gemini/gemini_doc)|
|[gemini_test2](https://github.com/kobongsoo/moai/blob/master/model_test/gemini/geminai_test2.ipynb)|구글 gemini 모델 Gemini API 연동 테스트..**GOOGLE_API_KEY 파일 발급 필요**|gemini API 연동 샘플 코드들 : [gemini](https://github.com/kobongsoo/moai/tree/master/model_test/gemini/gemini_doc)|


## 팁
huggingface 로그인 방법
- huggingface 모델을 실행할때(gemma등) 간혹 hugginface 로그인을 필요로 한다. 이때 아래처럼 token을 입력해서 로그인 해야 함.
```
import huggingface_hub
huggingface_hub.login(token='hf_xxxx')
```




