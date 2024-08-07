#!pip install pysqlite
import sqlite3 as sq
import pandas as pd
import uuid
#--------------------------------------------------------------------------------
# 호출 예시
# from utils import sqliteDB
# db=sqliteDB('kakao.db')
# 생성
# db.execute("CREATE TABLE user_mode (id text primary key, mode integer)") 
# 추가 리스트 여러개
# query = "INSERT INTO user_mode (id, mode) VALUES (?, ?)"
# data = [("6555cbd9cb76d42cb29078a4", 1), ("6555cbd9cb76d42cb29078a6", 2)]
# db.insert_list(query, data)
# 추가 1개
#id = "6555cbd9cb76d42cb29078a4"
#query = f"INSERT INTO user_mode (id, mode) VALUES ('{id}', 1)"
#db.execute(query)
# select
# query = "SELECT * FROM user_mode"
# df = db.select(query)
# print(df)
# 삭제 
#id = "6555cbd9cb76d42cb29078a4"
#query = f"DELETE FROM user_mode WHERE id = '{id}'"
#db.execute(query)
#--------------------------------------------------------------------------------
class SqliteDB:
    def __init__(self, dbname:str, assistants_len:int=3):
        assert dbname, f'dbname is empty'
        
        self.dbname = dbname
        
        self.assistants_len = assistants_len  # gpt 이전 대화 저장 계수
        
        # 연결할 때
        self.conn = sq.connect(self.dbname)
        
        # Cursor 객체 생성
        self.c = self.conn.cursor()
        #print("생성자 호출")
        
    def __del__(self):
        #print("종료 호출")
        if self.c:
            #print("self.c.close()")
            self.c.close()
            
        if self.conn:
            #print("self.conn.close()")
            self.conn.close()
     
      # SELECT * FROM user_mode WHERE id = 'uxssxxkd' => df로 리턴함
    def select(self, dbquery:str):
        df = pd.read_sql_query(dbquery, self.conn)
        return df
    
    def insert_list(self, dbquery:str, data:list):
        assert dbquery, f'dbquery is empty'
        assert len(data) > 0, f'data is empyt'
        
        error:int = 0
        try:
            self.c.executemany(dbquery, data)
            self.conn.commit()
            return error
        except Exception as e:
            print(f'[error]insert_list=>{e}')
            error = 1002
            self.conn.rollback()
            return
      
    # UPDATE user_mode SET mode = 1 WHERE id = 'uxssxxkd'
    # DELETE FROM user_mode WHERE id = 'uxssxxkd'
    def execute(self, dbquery:str):
        assert dbquery, f'dbquery is empty'
        
        error:int = 0
        try:
            self.c.execute(dbquery)
            self.conn.commit()
        except Exception as e:
            print(f'[error]execute: {dbquery}=>{e}')
            error = 1002
            self.conn.rollback()
            return
        
    def rollback(self):
        self.conn.rollback()
        
    def close(self):
        self.c.close()
        self.conn.close()
    #----------------------------------------------
    # user_mode 관련 
    # user_mode 테이블 : id 입력 시 해당 모드 출력 
    def select_user_mode(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        dbquery = f"SELECT * FROM user_mode WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
        if len(df) > 0:
            return df['mode'][0]
        else:
            return -1
        
    # user_mode 테이블 :id 있으면 mode 업데이트, 없으면 추가
    def insert_user_mode(self, user_id:str, user_mode:int):
        assert user_id, f'user_id is empty'
        assert user_mode > -1, f'user_mode is wrong'
        
        try:
            res = self.select_user_mode(user_id)
            if res == -1: # 없으면 추가
                dbquery = f"INSERT INTO user_mode (id, mode) VALUES ('{user_id}', {user_mode})"
            else: # 있으면 업데이트
                dbquery = f"UPDATE user_mode SET mode = {user_mode} WHERE id = '{user_id}'"

            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_user_mode=>error:{e}')
            return 1001
        
    # user_mode 테이블 :해당 id 있으면 삭제
    def delete_user_mode(self, user_id:str):
        assert user_id, f'user_id is empty'
        res = self.select_user_mode(user_id)
        
        if res > -1: # 있으면 제거
            dbquery = f"DELETE FROM user_mode WHERE id = '{user_id}'"
            self.c.execute(dbquery)
            self.conn.commit()
        
    #----------------------------------------------    
    # setting 관련 
    # [bong][2024-06-03] extraid:개인문서검색시 사용할 별칭id 추가함.
    # [bong][2024-04-18] LLM 필드 추가함 (LLM=0,1 (0=GPT, 1=Gemma)
    # setting 테이블 : id 입력 시 해당 site(naver, google) 출력 
    # userdb.execute('CREATE TABLE setting(id TEXT, site TEXT, prequery TEXT)')  # setting 테이블 생성
    def select_setting(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        dbquery = f"SELECT * FROM setting WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)

        if len(df) > 0:
            #print(df['site'])
            
            response:dict={}
            response['id']=df['id'][0]
            response['extraid']=df['extraid'][0] # [bong][2024-06-03] 별칭(extra_id) 추가.
            response['site']=df['site'][0]
            response['prequery']=df['prequery'][0]
            response['llmmodel']=df['llmmodel'][0]
            return response
        else:
            return -1
        
    # [bong][2024-04-18] LLM 필드 추가함 (LLM=0,1 (0=GPT, 1=Gemma)
    # search_site 테이블 :id 있으면 site 업데이트, 없으면 추가
    def insert_setting(self, user_id:str, extra_id:str, site:str, prequery:int, llmmodel:int):
        
        assert user_id, f'user_id is empty'
        #assert extra_id, f'extra_id is empty'
        assert site, f'site is empty'
        assert prequery >=0, f'prequery is wrong'
        assert llmmodel >=0, f'llmmodel is wrong'

        try:
            # *[중요] 입력한 extraid가 다른사용자가 사용중이면 1002 에러 리턴함.
            dbquery = f"SELECT * FROM setting WHERE extraid='{extra_id}' and id!='{user_id}'"
            df = pd.read_sql_query(dbquery, self.conn)
            if len(df) > 0:
                return 1002
            
            res = self.select_setting(user_id)
            #print(f'[insert_setting]=>res:{res}')
                
            if res == -1: # 없으면 추가
                dbquery = f"INSERT INTO setting (id, extraid, site, prequery, llmmodel) VALUES ('{user_id}', '{extra_id}', '{site}', {prequery}, {llmmodel})"
            else: # 있으면 업데이트
                dbquery = f"UPDATE setting SET extraid='{extra_id}', site='{site}', prequery={prequery}, llmmodel={llmmodel} WHERE id = '{user_id}'"

            #print(f'[insert_setting]=>dbquery:{dbquery}')
            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_setting=>error:{e}')
            return 1001
   
    # search_site 테이블 :해당 id 있으면 삭제
    def delete_setting(self, user_id:str):
        assert user_id, f'user_id is empty'
        res = self.select_setting(user_id)
        
        if res != -1: # 있으면 제거
            dbquery = f"DELETE FROM setting WHERE id = '{user_id}'"
            self.c.execute(dbquery)
            self.conn.commit()
    #----------------------------------------------           
    # gpt 지난 기억 assistants 메시지 관련
    def select_assistants(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        assistants:list = []
        dbquery = f"SELECT * FROM assistants WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
               
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['uid']=df['uid'][idx]
                data['prequery']=df['prequery'][idx]
                data['preanswer']=df['preanswer'][idx]
                assistants.append(data)

            return assistants
        else:
            return -1
        
    # insert_assistants
    def insert_assistants(self, user_id:str, prequery:str, preanswer:str):
        
        assert user_id, f'user_id is empty'
        assert preanswer, f'preanswer is empty'
        unique_id:str = ""

        # [*중요] ' 문자열 db 입력시 에러나므로 공백으로 치환함
        prequery = prequery.replace("'", " ")
        preanswer = preanswer.replace("'", " ")
        
        try:
            
            res = self.select_assistants(user_id)
            #print(f'[insert_assistants]=>res:{res}')
            
            # 800 글자보다 크면 799 글자까지만 저장해둠.
            if len(preanswer) > 800:
                preanswer = preanswer[0:799]
                
            if res != -1: # 3개 이상이면 맨 앞에서 삭제
                if len(res) > self.assistants_len-1:
                    unique_id = res[0]['uid']
                    dbquery = f"DELETE FROM assistants WHERE id = '{user_id}' and uid = '{unique_id}'"
                    self.c.execute(dbquery)
                    self.conn.commit()
            
            # UUID4를 사용하여 랜덤한 유니크한 ID 생성
            unique_id:str = str(uuid.uuid4())
            
            dbquery = f"INSERT INTO assistants (uid, id, prequery, preanswer) VALUES ('{unique_id}','{user_id}', '{prequery}', '{preanswer}')"
            #print(f'[insert_assistants]=>dbquery:{dbquery}')
            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_assistants=>error:{e}')
            return 1001
        
    # assistants 테이블 :해당 id 있으면 삭제
    def delete_assistants(self, user_id:str):
        assert user_id, f'user_id is empty'
        res = self.select_assistants(user_id)
        
        if res != -1: # 있으면 모두 제거
            dbquery = f"DELETE FROM assistants WHERE id = '{user_id}'"
            self.c.execute(dbquery)
            self.conn.commit()
    #----------------------------------------------           
    # 퀴즈 테이블 관련
    # id => key 값, type=100: last 질문과응답, type=0~5 : 퀴즈 질문과 응답, userid:사용자 id, query:질문, response: 답변, answer: 퀴즈 정답, info: 퀴즈 설명
    def select_quiz(self, userid:str, type:int=100):
        assert userid, f'userid is empty'

        if type == 100:
            dbquery = f"SELECT * FROM quiz WHERE userid='{userid}' and type={type}"
        else:
            dbquery = f"SELECT * FROM quiz WHERE userid='{userid}' and type!=100"
            
        df = pd.read_sql_query(dbquery, self.conn)

        quizes:list = []
        quize_num:int = -1
        
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['type']=df['type'][idx]
                data['userid']=df['userid'][idx]
                data['query']=df['query'][idx]
                data['response']=df['response'][idx]
                data['answer']=df['answer'][idx]
                data['info']=df['info'][idx]
                quizes.append(data)

                quize_num = df['type'][idx]  # *퀴즈계수는 맨마지막 데이터에 type 번호임.

            return quizes, quize_num
        else:
            return -1, quize_num
        
    # insert_quize
    # id => key 값, type=100: last 질문과응답, type=0~5 : 퀴즈 질문과 응답, userid:사용자 id, query:질문, response: 답변, answer: 퀴즈 정답, info: 퀴즈 설명
    def insert_quiz(self, type:int, userid:str, query:str, response:str="", answer:str="", info:str=""):
        
        assert type > -1, f'type is wrong'
        assert userid, f'userid is empty'
        assert query, f'query is empty'

        unique_id:str = ""

        # [*중요] ' 문자열 db 입력시 에러나므로 공백으로 치환함
        query = query.replace("'", " ")
        response = response.replace("'", " ")
        answer = answer.replace("'", " ")
        info = info.replace("'", " ")
        
        try:
            dbquery = f"SELECT * FROM quiz WHERE userid='{userid}' and type={type}"
            df = pd.read_sql_query(dbquery, self.conn)
                              
            if len(df) > 0: # 똑같은 type이 있으면 기존거 삭제
                unique_id = df['id'][0]
                dbquery = f"DELETE FROM quiz WHERE userid = '{userid}' and id = '{unique_id}'"
                self.c.execute(dbquery)
                self.conn.commit()
            
            # UUID4를 사용하여 랜덤한 유니크한 ID 생성
            unique_id:str = str(uuid.uuid4())
            
            dbquery = f"INSERT INTO quiz (id, type, userid, query, response, answer, info) VALUES ('{unique_id}',{type}, '{userid}', '{query}', '{response}', '{answer}', '{info}')"
            #print(f'[insert_quiz]=>dbquery:{dbquery}')
            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_quiz=>error:{e}')
            return 1001
        
    # quiz 테이블 :해당 id 있으면 삭제
    def delete_quiz_all(self, userid:str):
        assert userid, f'userid is empty'

        dbquery = f"SELECT * FROM quiz WHERE userid='{userid}'"
        df = pd.read_sql_query(dbquery, self.conn)
        
        if len(df) > 0: # 있으면 모두 제거
            dbquery = f"DELETE FROM quiz WHERE userid = '{userid}'"
            self.c.execute(dbquery)
            self.conn.commit()
            
    # quiz 테이블중 퀴즈인 것만 삭제 (type!=100 인것)
    def delete_quiz(self, userid:str):
        assert userid, f'userid is empty'
        res = self.select_quiz(userid=userid, type=1)
        
        if res != -1:
            dbquery = f"DELETE FROM quiz WHERE userid = '{userid}' and type!=100"
            self.c.execute(dbquery)
            self.conn.commit()
            
    # quiz 테이블 :해당 id에 지정한 type만  있으면 삭제
    def delete_quiz_type(self, userid:str, type:int):
        assert userid, f'userid is empty'
        res = self.select_quiz(userid=userid, type=type)
        
        if res != -1:
            dbquery = f"DELETE FROM quiz WHERE userid = '{userid}' and type={type}"
            self.c.execute(dbquery)
            self.conn.commit()
    #----------------------------------------------    
    # [bong][2024-06-03] 개인문서검색 관리 테이블
    # usermgr 관련 
    # usermgr 테이블에 있는 모든 id와 extraid 불러옴. 
    def select_usermgr_all(self):      
        dbquery = f"SELECT * FROM usermgr"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata

    # usermgr 테이블 
    def select_usermgr_extraid(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        dbquery = f"SELECT * FROM usermgr WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
        if len(df) > 0:
            return 0, df['extraid'][0]
        else:
            return -1, None
        
    # usermgr 테이블 :id 있으면 extra 업데이트, 없으면 추가
    def insert_usermgr_extraid(self, user_id:str, extraid:str):
        assert user_id, f'user_id is empty'
        assert extraid, f'extraid is empty'
        
        try:
            status, res = self.select_usermgr_extraid(user_id)
            print(f'*[insert_usermgr_extraid] status: {status}, res:{res}')
            
            if status == -1: # 없으면 추가
                dbquery = f"INSERT INTO usermgr (id, extraid) VALUES ('{user_id}', '{extraid}')"
            else: # 있으면 업데이트
                dbquery = f"UPDATE usermgr SET extraid = '{extraid}' WHERE id = '{user_id}'"

            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_usermgr_extraid=>error:{e}')
            return 1001
        
    # usermgr 테이블 :해당 id 있으면 삭제
    def delete_usermgr_extraid(self, user_id:str):
        assert user_id, f'user_id is empty'
        status, res = self.select_usermgr_extraid(user_id)

        try:
            if status == 0: # 있으면 제거
                dbquery = f"DELETE FROM usermgr WHERE id = '{user_id}'"
                self.c.execute(dbquery)
                self.conn.commit()
            return 0
        except Exception as e:
            print(f'delete_usermgr_extraid=>error:{e}')
            return 1001

    # 입력한 extraid가 있는지 검사
    def check_usermgr_extraid(self, extraid:str):
        assert extraid, f'extraid is empty'

        dbquery = f"SELECT * FROM usermgr WHERE extraid='{extraid}'"
        df = pd.read_sql_query(dbquery, self.conn)
        if len(df) > 0:
            return 0, df['id'][0]
        else:
            return -1, None
    #----------------------------------------------    
    # [bong][2024-06-13] music 관리 테이블
    # music 관련 
    # music 테이블에 있는 모든 사용자 데이터 불러옴. 
    def select_music_all(self):      
        dbquery = f"SELECT * FROM music"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                data['musicid1']=df['musicid1'][idx]
                data['musicid2']=df['musicid2'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata

    # music 테이블에 해당 user_id 데이터만 불러옴
    def select_music(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        dbquery = f"SELECT * FROM music WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                data['musicid1']=df['musicid1'][idx]
                data['musicid2']=df['musicid2'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata
        
    # music 테이블 :id 있으면 업데이트, 없으면 추가
    def insert_music(self, user_id:str, extraid:str, musicid1:str, musicid2:str):
        assert user_id, f'user_id is empty'
        assert musicid1, f'musicid1 is empty'
        assert musicid2, f'musicid2 is empty'
        
        try:
            status, res = self.select_music(user_id)
            #print(f'*[insert_music] status: {status}, res:{res}')
            
            if status == -1: # 없으면 추가
                dbquery = f"INSERT INTO music (id, extraid, musicid1, musicid2) VALUES ('{user_id}', '{extraid}', '{musicid1}', '{musicid2}')"
            else: # 있으면 업데이트
                dbquery = f"UPDATE music SET extraid = '{extraid}', musicid1='{musicid1}', musicid2='{musicid2}' WHERE id = '{user_id}'"

            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_music=>error:{e}')
            return 1001
        
    # music 테이블 :해당 id 있으면 삭제
    def delete_music(self, user_id:str):
        assert user_id, f'user_id is empty'
        status, res = self.select_music(user_id)

        try:
            if status == 0: # 있으면 제거
                dbquery = f"DELETE FROM music WHERE id = '{user_id}'"
                self.c.execute(dbquery)
                self.conn.commit()
            return 0
        except Exception as e:
            print(f'delete_music=>error:{e}')
            return 1001
    #----------------------------------------------    
    # [bong][2024-06-13] musiclist 관리 테이블
    # musiclist 관련 
    # musiclist 테이블에 있는 모든 사용자 데이터 불러옴. 
    # => id TEXT, extraid TEXT, m_id TEXT, m_title TEXT, m_lyric TEXT, m_audiourl TEXT, m_videourl TEXT, m_imageurl TEXT, date_time TEXT
    def select_musiclist_all(self):      
        dbquery = f"SELECT * FROM musiclist"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                data['m_id']=df['m_id'][idx]
                data['m_title']=df['m_title'][idx]
                data['m_lyric']=df['m_lyric'][idx]
                data['m_audiourl']=df['m_audiourl'][idx]
                data['m_videourl']=df['m_videourl'][idx]
                data['m_imageurl']=df['m_imageurl'][idx]
                data['date_time']=df['date_time'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata

    # musiclist 테이블에 해당 user_id 데이터만 불러옴
    def select_musiclist(self, user_id:str):
        assert user_id, f'user_id is empty'
        
        dbquery = f"SELECT * FROM musiclist WHERE id='{user_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                data['m_id']=df['m_id'][idx]
                data['m_title']=df['m_title'][idx]
                data['m_lyric']=df['m_lyric'][idx]
                data['m_audiourl']=df['m_audiourl'][idx]
                data['m_videourl']=df['m_videourl'][idx]
                data['m_imageurl']=df['m_imageurl'][idx]
                data['date_time']=df['date_time'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata

    # musiclist 테이블에 해당 m_id 데이터만 불러옴
    def select_musiclist_musicid(self, music_id:str):
        assert music_id, f'music_id is empty'
        
        dbquery = f"SELECT * FROM musiclist WHERE m_id='{music_id}'"
        df = pd.read_sql_query(dbquery, self.conn)
        userdata:list=[]
        if len(df) > 0:
            for idx in range(len(df)):
                data:dict = {}
                data['id']=df['id'][idx]
                data['extraud']=df['extraid'][idx]
                data['m_id']=df['m_id'][idx]
                data['m_title']=df['m_title'][idx]
                data['m_lyric']=df['m_lyric'][idx]
                data['m_audiourl']=df['m_audiourl'][idx]
                data['m_videourl']=df['m_videourl'][idx]
                data['m_imageurl']=df['m_imageurl'][idx]
                data['date_time']=df['date_time'][idx]
                userdata.append(data)

            return 0, userdata
        else:
            return -1, userdata
        
    # musiclist 테이블 :무조건업데이트
    def insert_musiclist(self, user_id:str, extraid:str, m_id:str, m_title:str, m_lyric:str, m_audiourl:str, m_videourl:str, m_imageurl:str, date_time:str):
        assert user_id, f'user_id is empty'
        
        try:
            status, res = self.select_musiclist_musicid(m_id)
            print(f'*[insert_musiclist] status: {status}, res:{res}')
                          
            if status == -1:  # 없으면 추가
                dbquery = f"INSERT INTO musiclist (id, extraid, m_id, m_title, m_lyric, m_audiourl, m_videourl, m_imageurl, date_time) VALUES ('{user_id}', '{extraid}', '{m_id}', '{m_title}', '{m_lyric}', '{m_audiourl}', '{m_videourl}', '{m_imageurl}', '{date_time}')"
            else:
                dbquery = f"UPDATE musiclist SET extraid = '{extraid}', m_title='{m_title}', m_lyric='{m_lyric}', m_audiourl='{m_audiourl}', m_videourl='{m_videourl}', m_imageurl='{m_imageurl}', date_time='{date_time}' WHERE m_id = '{m_id}'"
            self.c.execute(dbquery)
            self.conn.commit()
            return 0
        except Exception as e:
            print(f'insert_musiclist=>error:{e}')
            return 1001
        
    # musiclist 테이블 :해당 id 있으면 삭제
    def delete_musiclist(self, user_id:str):
        assert user_id, f'user_id is empty'
        status, res = self.select_musiclist(user_id)

        try:
            if status == 0: # 있으면 제거
                dbquery = f"DELETE FROM musiclist WHERE id = '{user_id}'"
                self.c.execute(dbquery)
                self.conn.commit()
            return 0
        except Exception as e:
            print(f'delete_musiclist=>error:{e}')
            return 1001
        