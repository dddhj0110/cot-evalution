# checkers/base.py
from openai import OpenAI
from transformers import AutoTokenizer
from traceback import format_exc

class Evaluator:
    """
    作为所有 Checker 的基类, 提供与 LLM 交互或其他公共功能
    """
    def __init__(self, **kwargs):
        # 初始化 LLM 客户端
        self.api_key = kwargs.pop("api_key", "EMPTY")
        self.base_url = kwargs.pop("base_url", "http://172.18.1.3:12345/v1")
        self.model = kwargs.pop("model", "deepseek-reasoner")
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.tokenizer = AutoTokenizer.from_pretrained('/data1/models/DeepSeek-R1')
        # 剩余参数存入 self.kwargs
        self.kwargs = kwargs

    def calc_text_token(self, text_data):
        tokens = self.tokenizer(text_data, return_tensors="pt", max_length=32765,truncation=True)
        token_count = len(tokens['input_ids'][0]) 
        #decoded_string = self.tokenizer.decode(tokens['input_ids'][0], skip_special_tokens=True)
        
        return token_count
    
    def _create_request(self, text, system=None):
        """构造纯文本请求格式"""
        if system:
            return[
                {"role": "system", "content" : [{"text": system, "type":"text"}]},  # 系统消息
                {"role": "user", "content" : [{"text": text, "type":"text"}]}  # 用户消息
            ]
        else:
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                        }
                    ]
                }
            ]
    def request_llm_stream(self, text_data, max_tokens=1024, temperature=0.6,system=None):
        """流式文本分析，返回生成的结果"""
        try:           
            messages = self._create_request(f"{text_data}", system)
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.6,
                stream=True
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content  # 使用 yield 生成器
        except Exception as e:
            print(f"Error: {e}")
            yield f"Error: {e}" # 流式返回错误信息


    def request_llm(self, text_data, max_tokens=1024, temperature=0.6,system=None):
        """通用文本分析，支持流式和非流式返回"""
        try:
            # 调用流式接口，不论stream值是否为True
            result = ""
            for chunk in self.request_llm_stream(text_data, max_tokens, system):
                result += chunk
                #print ('result===============', chunk)
            return result

        except Exception as e:
           
            print("error!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", format_exc())
            return ""
