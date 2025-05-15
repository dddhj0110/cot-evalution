# checkers/reflection_checker.py
from .base import Evaluator

class ReflectionChecker(Evaluator):
    """
    用于对思考过程中的反思内容进行打分
    """
    def check(self, think_text):
        """
        计算think_text中reflection_phrases出现的频率，并根据文本长度进行标准化处理，
        同时限制最高得分为MAX_SCORE。
        """ 
        MAX_SCORE = 100  # 设定最高得分上限
        reflection_phrases = ['重新审视', '重新检查', '或许', '可能','等等','等一下'] 
        score = sum(think_text.count(phrase) for phrase in reflection_phrases)
        # text_length = len(think_text)
        # if text_length > 0:
        #     normalized_score = (score / text_length) * 1000 
        # else:
        #     normalized_score = 0
        return min(score, MAX_SCORE)
