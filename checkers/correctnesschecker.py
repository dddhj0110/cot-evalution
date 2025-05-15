# checkers/correctness_checker.py
from .base import Evaluator
import re
class CorrectnessChecker(Evaluator):
    """
    将给定答案与参考答案进行比较, 判断答案是否正确
    """

    def check(self,answer, reference_answer):
        if answer is None or reference_answer is None:
            return 0
        
        answer_cleaned = str(answer).strip()
        reference_answer_cleaned = str(reference_answer).strip()
        try:
            if float(answer_cleaned) == float(reference_answer_cleaned):
                return 15
        except ValueError:
            if answer_cleaned == reference_answer_cleaned:
                return 15
        return 0
    
    def compare_answers(self,model_output: str, reference_answer: str):
        if model_output is None or reference_answer is None:
            return 0
        question=f"""
您是一个金融专家。用户将针对一个问题进行解答，并给出分析过程和结论。您的工作是根据用户给出的分析过程和结论，以及正确的结论，判断分析尝试是否正确。如果分析过程能够得出明确的数字或结论，应该没有歧义。如果分析过程涉及详细的推理步骤，您应根据推理过程是否正确来判断该尝试，并在推理过程正确的前提下给出评分。

用户将以以下格式提供用户答案和标准答案：

用户答案：
{model_output}
标准答案:
{reference_answer}

解释您的分析推理过程，然后根据以下五分制评分标准给出分数：
15 分 = 完全正确：分析过程完全正确，最终结论准确无误。
10 分 = 较好：分析过程基本正确，只有一些小错误或遗漏。
5 分 = 一般：分析过程部分正确，但有明显错误。
0 分 = 非常差：分析过程完全错误，结论与正确答案相差甚远。

-输出格式为：
<result>（输出答案）</result>
-<result></result>之间的内容只应该是得分，即数值
"""
        inputokens=self.calc_text_token(question)    
        model_answer = self.request_llm(question,16348-inputokens)
        stripped_answer = self.extract_result_content(model_answer)
        #print("得分:",stripped_answer)
        if re.fullmatch(r"[0-9]+(\.[0-9]+)?", stripped_answer):
            return int(float(stripped_answer))
        return 0
    
    def extract_result_content(self,content):
        pattern = r"<result>(.*?)</result>"  # 非贪婪匹配，匹配任意字符（包括换行）
        match = re.search(pattern, content, re.DOTALL)  # re.DOTALL 使 . 能匹配换行符
        return match.group(1).strip() if match else None  # 去除首尾空白字符
