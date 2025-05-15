# checkers/logic_checker.py
from .base import Evaluator
import re

class LogicChecker(Evaluator):
    """
    用于评估答案思考过程的逻辑正确性和支持度
    """
    errors=[]
    def check(self,reasoning_process):
        template=f"""
### 评分过程请使用中文
### 请严格对输入的思考过程进行打分,输入如下：
{reasoning_process}

### 计算问题和答案之间的逻辑蕴含度分数(Ent)，要求严格按照以下步骤进行评估：
- 所有过程均基于答题者的回答
- 请使用Q：问题，S：思考步骤来标识过程，且问题不是步骤
- 阅读问题和解答步骤，并判断每个步骤是否准确地由问题得出
- 如果某一个子句不仅与问题相关，而且其逻辑和数值计算都是准确无误的，则记为1；否则，记为0
- 如果某一步骤包含逻辑或数值上的错误，那么即使这一步骤看起来与问题有关联，也应当认为它是错误的，记为0
- 计算整个问题和答案的Ent值，公式为：
   Ent = (∑_1^n e_i) / n，其中 e_i = {{ 1 if accurate and relevant to Q, 0 otherwise }}
- 请你参考并模仿如下Ent值评分步骤，并保持格式一致：
Q: Emily is planning a party for her friends. She has bought 5 boxes of cupcakes, with each box containing 12 cupcakes. She also made 30 homemade cookies. If she wants to give each of her 15 friends an equal amount of treats (cupcakes and cookies combined), how many treats will each friend receive?
S1: Emily bought 5 boxes of cupcakes, each containing 12 cupcakes, so she has 5 * 12 = 60 cupcakes.
    - Relevance: 1 (This step is relevant as it contributes to the total number of treats)
S2: She also made 30 homemade cookies.
    - Relevance: 1 (This step is relevant as it adds to the total number of treats)
S3: In total, she has 60 + 30 = 90 treats.
    - Relevance: 1 (This step is relevant as it calculates the total number of treats)
S4: She wants to distribute these equally among her 15 friends.
    - Relevance: 1 (This step is relevant as it introduces the requirement for equal distribution)
S5: So each friend will receive 90 / 15 = 6 treats.
    - Relevance: 1 (This step is relevant as it answers the question)
S6: The answer is 6.
    - Relevance: 1 (This step is relevant as it confirms the answer)
Ent Calculation: (1+1+1+1+1+1) / 6 = 6 / 6 = 1

### 计算思考过程中每一次回答的逻辑支持度分数(Fav)，要求严格按照以下步骤进行评估：
- 所有过程均基于答题者的回答
- 仅需对思考过程的逐个步骤评分，并判断从第二步开始的每一步骤是否由前面的所有步骤支持。
- 每一步必须基于前面步骤提供的信息进行正确且合乎逻辑的推断。如果某一步骤包含逻辑或算术错误，则记为0。
- 即判断s2是否由s1支持，s3是否由s2,s1支持，s4是否由s3,s2,s1支持，以此类推。
- 计算整个思维链的Fav值，n的值等于步骤数目,分母为n-1，公式为：
   Fav = (∑_2^n f_i) / (n-1)，其中 f_i = {{ 1 if support(a_(1:i-1) → a_i), 0 otherwise }}
- 请你参考并模仿如下Fav值评分步骤，并保持格式一致：
Step 1: Emily bought 5 boxes of cupcakes, each containing 12 cupcakes, so she has 5 * 12 = 60 cupcakes.
  - Support: N/A (First step, no prior steps to support)
Step 2: She also made 30 homemade cookies.
  - Support: 0 (Step 1 doesn't need to support Step 2 as they are independent facts)
Step 3: In total, she has 60 + 30 = 90 treats.
  - Support: 1 (Step 3 is supported by Steps 1 and 2)
Step 4: She wants to distribute these equally among her 15 friends.
  - Support: 1 (Step 4 is supported by Step 3, which gives the total number of treats)
Step 5: So each friend will receive 90 / 15 = 6 treats.
  - Support: 1 (Step 5 is supported by Steps 3 and 4)
Step 6: The answer is 6.
  - Support: 1 (Step 6 is supported by Step 5)
  
Fav Calculation: (0+1+1+1+1) / (6-1) = 4 / 5 = 0.8

### 在计算结束以后，请遵从下列格式输出
<answer>
[Ent,Fav]=[XXX, YYY]
</answer>

"""
        inputokens=self.calc_text_token(template)
        result_score = self.request_llm(template, 16348-inputokens)

        fav_score, ent_score = self.parse_result(result_score)  # 需要实现parse_result方法来解析结果
        
        return result_score,fav_score*10, ent_score*10
    
    
    def parse_result(self,result_text):
        pattern = r'\[Ent,Fav\]=\[([\d.]+),\s*([\d.]+)\]'
        match = re.search(pattern, result_text)
    
        if match:
            ent_score = float(match.group(1))
            fav_score = float(match.group(2))
            return fav_score, ent_score
        else:
            # 如果没有找到匹配的模式，返回默认值或抛出异常
            self.errors.append("无法从结果文本中解析出Ent和Fav分数")    
            return -1,-1
    