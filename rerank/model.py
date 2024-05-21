import os
import time
from BCEmbedding import RerankerModel
#--------------------------------------------------------------------------------
# https://huggingface.co/maidalun1020/bce-reranker-base_v1
# !pip install BCEmbedding==0.1.1
#--------------------------------------------------------------------------------
class ReRank:
    def __init__(self, model_path:str, device:str='cpu'):
        assert model_path, f'model_path is empty'
        
        self.model_path = model_path
        self.device = device 
        
        self.model = RerankerModel(model_name_or_path=self.model_path, device=self.device)
        
    def __del__(self):
        print("ReRank 종료 호출")
     
    # 스코어 구하기
    # -in: 쿼리, 검색된 내용
    # -out : ReRank 스코어 (리스트) => [0.5889798402786255, 0.6205288171768188, 0.3546408891677856, 0.4557476878166199]
    def compute_score(self, query:str, contexts:list):
        assert query, f'query is empty'
        assert len(contexts) > 0, f'contexts is empyt'
        
        start_time = time.time()

        # construct sentence pairs
        sentence_pairs = [[query, context] for context in contexts]

        # method 0: calculate scores of sentence pairs
        scores = self.model.compute_score(sentence_pairs)
        
        end_time = time.time()
        formatted_elapsed_time = "{:.2f}".format(end_time - start_time)
        print(f'*time:{formatted_elapsed_time}')

        return scores
        
    # 내림차순 스코어로 정렬되어서 출력됨
    # -in: 쿼리, 검색된 내용
    # -out : results 스코어 (리스트) => [0.5889798402786255, 0.6205288171768188, 0.3546408891677856, 0.4557476878166199]
    def compute_rerank(self, query:str, contexts:list):
        assert query, f'query is empty'
        assert len(contexts) > 0, f'contexts is empyt'

        start_time = time.time()
    
        # method 1: rerank passages
        results = self.model.rerank(query, contexts)

        end_time = time.time()
        formatted_elapsed_time = "{:.2f}".format(end_time - start_time)
        print(f'*time:{formatted_elapsed_time}')

        return results
       