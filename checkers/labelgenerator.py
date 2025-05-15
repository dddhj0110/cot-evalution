# checkers/logic_checker.py
from .base import Evaluator
import re

max_token=5000

class LabelGenerator(Evaluator):
    def QA_difficulty(self,question,attempts,ref_ans):
        question=f"""{question}
#回答上述问题请遵循以下要求：
-回答需要以下列某一经济学家或数学家的视角，请随机挑选一位：
1.John Maynard Keynes,
2.Friedrich August von Hayek,
3.Robert Mundell,
4.John Nas,
5.Carl Friedrich Gauss
-要明确指出从哪个人的视角
-分步骤思考问题，每条思考应有逻辑，分步骤，逐步引导递进。
-解答过程请使用中文
-输出格式为：
<steps>（思考过程）</steps>
<result>（输出答案）</result>
-<steps></steps>之间的内容应该是分点分步骤的，例如1.2.3.4
-<result></result>之间的内容只允许为单个数值或字母
"""
        correct_count=0        
        model_answers=[]
        for _ in range(attempts):
            inputokens=self.calc_text_token(question)    
            model_answer = self.request_llm(question,16348-inputokens)
            model_answers.append(model_answer)
            predict_answer = self.abstract_content(model_answer)
            if predict_answer == ref_ans:
                correct_count += 1               
        pass_rate = round(correct_count / attempts, 2)
        return model_answers,pass_rate
       
    def clean_content(self, content):
        """
        清洗内容，去掉 <think></think> 标签及其中的内容。
        """
        # 使用正则表达式删除 <think></think> 标签及其中的内容
        cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        return re.search(r'[ABCD]', cleaned_content).group()
    
    def abstract_content(self, content):
        pattern = r"<result>\s*(([A-D])|(\d+(\.\d+)?))\s*</result>"
        match = re.search(pattern, content)
        if match is not None:
        # 检查是否是字母选项
            if match.group(2):  # 匹配到的是 A, B, C, D 中的一个
                answer = match.group(2)
            else:  # 否则是数字或小数
                answer = float(match.group(3)) if '.' in match.group(3) else int(match.group(3))
        else:
            print("Warning: Expected pattern not found in the model answer.")
            answer = -9999.0
        return answer
    
    def LT_difficulty(self,question,passage,ref_ans,attempts):
        question=f"""
[Passage]
{passage}
[Question]
{question}
#回答上述问题请遵循以下要求：
-question里包含几个内容相关的文本
-推理过程应主要依赖于从[Passage]文本中检索到的信息
-不应严重依赖其自身的知识库
-分步骤思考问题，每条思考应有逻辑，分步骤，逐步引导递进
-思考问题时，要求具有自我反思，自我纠错过程
-解答过程请使用中文
-输出格式为：
<steps>（思考过程）</steps>
<result>（输出答案）</result>
-<steps></steps>之间的内容应该是分点分步骤的，例如1.2.3.4
-<result></result>之间的内容不允许分段
"""
        correct_count=0        
        model_answers=[]
        correct_score=[]
        processes=[]
        for _ in range(attempts):
            inputokens=self.calc_text_token(question)    
            model_answer = self.request_llm(question,16348-inputokens)
            #print(model_answer,"\n")
            model_answers.append(model_answer)
            
            #仅保留答案
            predict_answer = self.extract_result_content(model_answer)
            score,process=self.compare_answers(predict_answer,ref_ans)
            processes.append(process)
            if score==15:
                print("\nOK\n")
                correct_count += 1 
            correct_score.append(score)            
        pass_rate = round(correct_count / attempts, 2)
        
        return model_answers,correct_score,processes,pass_rate
    def extract_result_content(self,content):
        pattern = r"<result>(.*?)</result>"  # 非贪婪匹配，匹配任意字符（包括换行）
        match = re.search(pattern, content, re.DOTALL)  # re.DOTALL 使 . 能匹配换行符
        return match.group(1).strip() if match else None  # 去除首尾空白字符
    
    def compare_answers(self,model_output: str, reference_answer: str):
        question=f"""
您是一个金融专家。用户将针对一个问题进行解答，并给出分析过程和结论。您的工作是根据用户给出的分析过程和结论，以及正确的结论，判断分析尝试是否正确。如果分析过程能够得出明确的数字或结论，应该没有歧义。如果分析过程涉及详细的推理步骤，您应根据推理过程是否正确来判断该尝试，并在推理过程正确的前提下给出评分。

用户将以以下格式提供用户答案和标准答案：

用户答案：
{model_output}
标准答案:
{reference_answer}

解释您的分析推理过程，然后根据以下三分制评分标准给出分数，评分时应优先核验结论一致性、主体完整性和细节准确性，避免因表述形式差异误判。：
0分（完全错误）：答案与问题核心无关，结论与正确答案完全矛盾，或包含严重错误（如虚构信息、曲解关键概念），且未覆盖任何核心要素。
5分（部分正确）：答案部分涉及正确内容，但存在以下问题之一：遗漏关键信息或核心主体；表述模糊、泛化（如用间接描述替代明确结论）；夹杂冗余或非必要信息，干扰核心结论。
10分（完全正确）：答案完整覆盖所有核心要素（如主体、事实、结论），结论与标准答案完全一致，表述准确清晰，允许合理的形式差异（如近义词替换、逻辑等效表达），且无错误或无关内容。

-输出格式为：
<result>（输出答案）</result>
-<result></result>之间的内容只应该是得分，即数值
"""
        inputokens=self.calc_text_token(question)    
        model_answer = self.request_llm(question,16348-inputokens,temperature=0.3)
        stripped_answer = self.extract_result_content(model_answer)
        #print("得分:",stripped_answer)
        if not stripped_answer:  # 如果是 None 或空字符串
            return 0,model_answer
        if re.fullmatch(r"[0-9]+(\.[0-9]+)?", stripped_answer):
            return int(float(stripped_answer)),model_answer
        return 0,None