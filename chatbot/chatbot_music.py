import os
import time
import asyncio
import threading
import httpx
import sys
import pytz
from datetime import datetime

def chatbot_check_create_music(settings:dict, data:dict, instance:dict, result:dict):

    status:int = 0
    datalist:list = []

    host = settings['SUNO_API_SERVER']
    query = data['query']
    user_id = data['userid']

    assert host, f'host is empty'
    assert query, f'query is empty'
    assert user_id, f'user_id is empty'

    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    suno = instance['suno']
    callback_template = instance['callback_template']
    api_url = settings['API_SERVER_URL']

    # 한국 시간대 설정
    korea_tz = pytz.timezone('Asia/Seoul')
    # 현재 한국 날짜와 시간
    korea_now = datetime.now(korea_tz)
    # 한국어 표준 날짜와 시간 형식으로 변환
    korea_now_str = korea_now.strftime('%Y-%m-%d %H:%M:%S')

    # query로 아래처럼 입력이 들어온다.
    # => "^음악생성확인^\n794b9481-cb93-4bf3-b265-d1c36c87b7f7, 694b9481-cb93-4bf3-b265-d1c36c87b7f7"
    # 1. 개행 문자('\n')를 기준으로 msg를 분리합니다.
    #parts = query.split('\n')
    # 2. 두 번째 부분(인덱스 1)에서 ','로 구분하여 리스트로 만듭니다.
    #ids = parts[1].split(', ')

    ids:list = []
    status1, res1 = userdb.select_music(user_id=user_id)
    if status1 == 0:
        ids.append(res1[0]['musicid1'])
        ids.append(res1[0]['musicid2'])
    else:
        myutils.log_message(f'\t[chatbot_check_create_music]select_music => error: {status1}')

    myutils.log_message(f'\t[chatbot_check_create_music] *ids=>{ids}')

    try:
        # 음악 파일(mp3,mp4) 목록 얻기
        # => 음악 ids 입력후 음악 파일(mp3,mp4) 목록 얻기  
        status, datalist = suno.getfile_by_ids(ids=ids, host=host, max_retries=1)
    except Exception as e:
        msg = f'{e}'
        myutils.log_message(f'\t[chatbot_check_create_music][error] {msg}')
        status = 102

    if status == 0:
        title = "🎧노래가 완성되었습니다.!\n[노래듣기] 버튼을 눌러주세요." 
        text = f'{datalist[0]["title"]}\n{datalist[0]["lyric"]}' # 제목/내용 출력
        ids:list = []
        for data in datalist:
            ids.append(data["video_url"])
            
            # 성공이면 db에 저장 
            m_id = data['id']
            m_title = data['title']
            m_lyric = data['lyric']
            m_audiourl = data['audio_url']
            m_videourl = data['video_url']
            m_imageurl = data['image_url']
            status1 = userdb.insert_musiclist(user_id=user_id, extraid="", m_id=m_id, m_title=m_title, m_lyric=m_lyric, m_audiourl=m_audiourl, m_videourl=m_videourl, m_imageurl=m_imageurl, date_time=korea_now_str)
            if status1 != 0:
                myutils.log_message(f'\t[chatbot_check_create_music][error] {status1}')
                
        template = callback_template.music_success_template(title=title, descript=text, user_id=user_id, music_url=ids)
    else:
        # 답변 설정
        title = "🎧노래 제작중..\n좀더 대기 후 [노래확인]버튼을 눌러 보세요." 
        text = "🕙노래 제작은 평균 3분~4분 걸립니다."
        template = callback_template.music_template(title=title, descript=text, api_url=api_url, user_id=user_id)

    result['error'] = status

    result['prompt'] = query
    result['query'] = query
    result['template'] = template
    result['docs'] = ids  # **음악 ids를 담음
        
    return result

    
def chatbot_create_music(settings:dict, data:dict, instance:dict, result:dict):

    # 음악 생성
    host = settings['SUNO_API_SERVER']
    prompt = data['query']
    user_id = data['userid']

    assert host, f'host is empty'
    assert prompt, f'prompt is empty'
    assert user_id, f'user_id is empty'
    
    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    suno = instance['suno']
    callback_template = instance['callback_template']
    api_url = settings['API_SERVER_URL']
    
    status:int = 0
    ids:list = []

    try:
        status, ids = suno.create(prompt=prompt, host=host)
    except Exception as e:
        myutils.log_message(f'\t[chatbot_create_music]==>suno.create fail=>{e}')
        id_manager.remove_id_all(user_id) # id 제거
        text = f"⚠️노래제작중 오류발생..(에러:{e})"
        template = callback_template.simpletext_template(text = text)
        result['error'] = 1001
        result['prompt'] = prompt
        result['query'] = prompt
        result['template'] = template
        result['docs'] = ids  # **음악 ids를 담음
        return result
    
    #ids:list = ['c4c0cb19-26f8-4a2d-b7b1-27c610f30e26', '694b9481-cb93-4bf3-b265-d1c36c87b7f7']
    
    # ids 없으면. 음악생성 실패한것이므로 에러 리턴
    if len(ids) < 2:
        id_manager.remove_id_all(user_id) # id 제거
        text = "⚠️노래제작에 실패. 다시 시도해 보십시오."
        template = callback_template.simpletext_template(text = text)
        result['error'] = 1002
    else:
        # 답변 설정
        title = "🎧노래 제작중..\n3~4분 대기 후에 [노래확인] 버튼을 눌러 보세요." 
        text = f"📝 {prompt}" 
        myutils.log_message(f'\t[chatbot_create_music]==>text:{text}')

        # extraid가 있으면 추가 
        status1, res1 = userdb.select_usermgr_extraid(user_id=user_id)
        extraid:str = ""
        if status1 == 0:
            extraid = res

        # music db에 추가 
        status1 = userdb.insert_music(user_id=user_id, extraid=extraid, musicid1=ids[0], musicid2=ids[1])
        if status1 != 0:
            myutils.log_message(f'\t[chatbot_create_music] insert_music fail!!=>error: {status1}')
            
        #idstr = ', '.join(ids) # list를 , 구분해서 str형으로 변환
        template = callback_template.music_template(title=title, descript=text, user_id=user_id, api_url=api_url)
        myutils.log_message(f'\t[chatbot_create_music]==>template:{template}')
        
        result['error'] = status

    result['prompt'] = prompt
    result['query'] = prompt
    result['template'] = template
    result['docs'] = ids  # **음악 ids를 담음
        
    return result

# 남은 용량 얻기.
def chatbot_get_music_limit(settings:dict, data:dict, instance:dict, result:dict):

    host = settings['SUNO_API_SERVER']
    prompt = data['query']
    user_id = data['userid']

    assert host, f'host is empty'
    assert prompt, f'prompt is empty'
    assert user_id, f'user_id is empty'
    
    myutils = instance['myutils']
    userdb = instance['userdb']
    id_manager = instance['id_manager']
    suno = instance['suno']
    callback_template = instance['callback_template']
    api_url = settings['API_SERVER_URL']

    result['prompt'] = prompt
    result['query'] = prompt

    try:
        status, res = suno.get_limit(host=host)
        text = f"===suno info===\n*총용량(월): {res['monthly_limit']}\n*남은용량 : {res['credits_left']}\n*사용량: {res['monthly_usage']}"
    except Exception as e:
        myutils.log_message(f'\t[chatbot_get_music_limit]==>suno.create fail=>{e}')
        id_manager.remove_id_all(user_id) # id 제거
        text = f"⚠️suno 용량얻기 오류발생..(에러:{e})"
        status = 1001

    template = callback_template.simpletext_template(text = text)
    myutils.log_message(f'\t[chatbot_get_music_limit]==>template:{template}')
    result['template'] = template
    result['error'] = status
    return result
    