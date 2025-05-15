# checkers/format_checker.py
from .base import Evaluator
import re

class FormatChecker(Evaluator):
    """
    用于检查文本中 <think> 和 <answer> 标签内容是否符合要求
    """
    errors=[]
    def check_think(self, text,threshold):
        think_pattern = r"<think>(.*?)</think>"
        think_match = re.search(think_pattern, text, re.DOTALL)
        score=0
        if think_match:
            score += 3  # 存在<think>标签加3分
            think_content = think_match.group(1).strip()
            if self.is_mostly_chinese(think_content, threshold):
                score += 5  # 内容正确再加5分
            else:
                self.errors.append("Warning: <think>标签内的内容不是严格使用中文回答。")
        else:
            self.errors.append("Error: 文本中没有找到<think>标签。")
        return score

    def check_answer(self, text):
        answer_pattern = r"<result>(.*?)</result>"
        answer_match = re.search(answer_pattern, text,re.DOTALL)
        print(answer_match)
        score=0
        if answer_match:
            score += 3  # 存在<answer>标签加3分
            answer_content = answer_match.group(1).strip()
            stripped_answer,flag=self.check_answer_format(answer_content)
            if flag:
                score += 5  # 内容格式正确再加5分
                print(f"Stripped Answer: {stripped_answer}, Score: {score}")
                return stripped_answer,score
            else:
               self.errors.append(f"Warning: 答案格式不符合要求。")
        else:
            self.errors.append("Error: 文本中没有找到<answer>标签。")
        return None,score
        
    @staticmethod
    def is_mostly_chinese(text, threshold=0.7):
        """
        检查给定的字符串是否大部分由中文字符组成
        """
        clean_text = re.sub(r'[^a-zA-Z\u4e00-\u9fff]', '', text)
    
        chinese_chars = sum('\u4e00' <= char <= '\u9fff' for char in clean_text)
        total_chars = len(clean_text)

        if total_chars == 0:
            return False

        return (chinese_chars / total_chars) >= threshold
    
    @staticmethod
    def check_answer_format(answer):
        stripped_answer = answer.strip()
        # 条件1：匹配数字或小数（如 "42" 或 "3.14"）
        if re.fullmatch(r"[0-9]+(\.[0-9]+)?", stripped_answer):
            return stripped_answer, True
    
        # 条件2：匹配单个大写字母选项（A/B/C/D）
        elif stripped_answer.upper() in ['A', 'B', 'C', 'D']:
            return stripped_answer, True
    
        # 条件3：如果内容没有分段（即不包含换行符 \n）
        elif '\n' not in stripped_answer:
            return stripped_answer, True
    
        # 其他情况均返回 False
        return None, False
    