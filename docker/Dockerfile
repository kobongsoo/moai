#base image
FROM bong9431/moai:0.9

#metatag
MAINTAINER bong9431
LABEL "title"="moai"
LABEL "model"="BERT&GPT"
LABEL "dbms"="elsticsearch 7.17.13"

#COPY
COPY ./moai ./

#workdir
WORKDIR /moai

#run (이미존재하면 에러남)
#RUN mkdir /log

#cmd
CMD uvicorn moai:app --host=0.0.0.0 --port=9000 --limit-concurrency=200 > /moai/log/server.log 2>&1
#CMD jupyter lab --ip=0.0.0.0 --port=9999 --allow-root
