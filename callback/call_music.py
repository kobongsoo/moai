import os
import time
import asyncio
import threading
import httpx
import sys

from typing import Union, Dict, List, Optional

sys.path.append('..')
from music import SUNO

def call_music(settings:dict, data:dict, instance:dict):

    userdb = instance['userdb']
    myutils = instance['myutils']
    callback_template = instance['callback_template']
    id_manager = instance['id_manager']
    suno = instance['suno']
    
    callbackurl = data['callbackurl']
    prompt = data['prompt']
    query = data['query']
    user_id = data['user_id']
    user_mode = data['user_mode']
    ids = data['docs']  # id 몯록을 얻어옴

    host = settings['SUNO_API_SERVER']
    
    myutils.log_message(f"-" * 50)
    myutils.log_message(f"\t[call_music][start]=>user_mode:{user_mode},ids:{ids},query:{query}")

    status:int = 0
    datalist:list=[]

    start_time = time.time()
    
    try:
        # 음악 파일(mp3,mp4) 목록 얻기
        # => 음악 ids 입력후 음악 파일(mp3,mp4) 목록 얻기  
        status, datalist = suno.getfile_by_ids(ids=ids, host=host)
    except Exception as e:
        msg = f'{error}=>{e}'
        myutils.log_message(f'\t[call_music][error] {msg}')
        status = 102
        
    if status == 0:
        myutils.log_message(f"-" * 50)
        myutils.log_message(f'\t*datalist:\n{datalist}')
        myutils.log_message(f'*제목:{datalist[0]["title"]}')
        myutils.log_message(f'*가사:{datalist[0]["lyric"]}')

        query = datalist[0]['title']      # 제목
        response = datalist[0]["lyric"]   # 가사
    else:
        query = "응답 에러"
        response = f"⚠️AI 에러가 발생하였습니다. 잠시 후 다시 질문해 주세요.\n({status})"

    # 소요된 시간을 계산합니다.
    end_time = time.time()
    el_time = "{:.2f}".format(end_time - start_time)

    template = callback_template.template_music(query=query, response=response, datalist=datalist, elapsed_time=el_time)     

    # id_manager 에 id 제거 :응답 처리중에는 다른 질문할수 없도록 lock 기능을 위한 user_id 제거
    id_manager.remove_id_all(user_id) # id 제거
    
    myutils.log_message(f"\t[call_music][end]=>time:{el_time}")
    myutils.log_message(f"-" * 50)
    
    return template
    