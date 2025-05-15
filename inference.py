import pandas as pd
import json
import argparse
import os
import csv
import importlib
import logging
from typing import Dict, List, Any, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """加载并验证配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 基本配置验证
    if "data_path" not in config:
        raise ValueError("Config must contain 'data_path'")
    if "checkers" not in config or not isinstance(config["checkers"], list):
        raise ValueError("Config must contain 'checkers' list")
    
    return config

def load_data(data_path: str) -> List[Dict[str, Any]]:
    """加载数据集"""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data path not found: {data_path}")
    
    ext = os.path.splitext(data_path)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(data_path, encoding='utf-8')
        elif ext == '.xlsx':
            df = pd.read_excel(data_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        return df.to_dict('records')
    except Exception as e:
        raise ValueError(f"Error loading data: {str(e)}")

def initialize_checker(checker_cfg: Dict[str, Any]) -> Any:
    """动态初始化检查器实例"""
    class_name = checker_cfg["class_name"]
    
    # 动态导入模块
    module_name = f"checkers.{class_name.lower()}"
    try:
        module = importlib.import_module(module_name)
        CheckerClass = getattr(module, class_name)
        return CheckerClass()
    except Exception as e:
        logger.error(f"Failed to initialize {class_name}: {str(e)}")
        raise

def process_method(checker_instance, method_cfg, example, input_path=" ", output_path=" "):
    """处理单个检查方法"""
    method_name = method_cfg["method_name"]
    if not hasattr(checker_instance, method_name):
        raise AttributeError(f"Method {method_name} not found in {checker_instance.__class__.__name__}")
    
    method_to_call = getattr(checker_instance, method_name)
    params = method_cfg.get("params", {})
    
    logger.info(f"Running {checker_instance.__class__.__name__}.{method_name}")
    try:
        #根据检查器类型准备不同参数
        if checker_instance.__class__.__name__ == "LabelGenerator":
            if method_name == "LT_difficulty":
                #model_answers,correct_score,processes,pass_rate = method_to_call(example["question"],example["RAG"],example["answer"], **params)
                return {}
            
        if checker_instance.__class__.__name__ == "FormatChecker":
            if method_name == "check_think":
                score = method_to_call(example["COT答案"], **params)
                return {"思考格式得分": score}
            elif method_name == "check_answer":
                stripped_answer, score = method_to_call(example["COT答案"], **params)
                return {
                    "答案格式得分": score
                }
                
        elif checker_instance.__class__.__name__ == "LogicChecker":
            if method_name == "check":
                logic_thinking, logic_fav_score, logic_ent_score = method_to_call(example["answer"], **params)
                return {
                    "逻辑打分过程": logic_thinking,
                    "句间逻辑支持得分": logic_fav_score,
                    "问答逻辑蕴含得分": logic_ent_score
                }
                
        elif checker_instance.__class__.__name__ == "ReflectionChecker":
            if method_name == "check":
                score = method_to_call(example["COT答案"], **params)
                return {"自我反思得分": score}
                
        elif checker_instance.__class__.__name__ == "CorrectnessChecker":
            if method_name == "check":
                # 使用FormatChecker处理后的stripped_answer
                stripped_answer = example.get("stripped_answer", example["COT答案"])
                score = method_to_call(stripped_answer, example["answer"], **params)
                return {"正确性得分": score}
            
        elif checker_instance.__class__.__name__ == "Filter":
            if method_name == "filter":
                res = method_to_call(example, **params)
                return res
                   
        return {f"{checker_instance.__class__.__name__}_{method_name}": "空result"}
        
    except Exception as e:
        logger.error(f"Error processing {method_name}: {str(e)}")
        return {}
    
def save_results(output_path, fieldnames, answer_record):
    """保存结果到文件（自动处理表头）"""
    # 检查文件是否存在
    file_exists = os.path.exists(output_path)
    
    with open(output_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # 如果文件不存在或为空，写入表头
        if not file_exists or os.stat(output_path).st_size == 0:
            writer.writeheader()
        
        writer.writerow(answer_record)
    
def main(config_path: str) -> None:
    """主执行流程"""
    try:
        # 1. 加载配置
        config = load_config(config_path)
        logger.info(f"Loaded config from {config_path}")
        
        # 2. 读取数据集
        examples = load_data(config["data_path"])
        logger.info(f"Loaded {len(examples)} RAG examples")
        
        # 2.5 生成COT
        cot_path = config["cot_path"]
        fieldnames = ['question', 'RAG', 'answer', '困难等级','COT答案',  '正确性得分', '正确性过程']
        
        for example in examples:
            for checker_cfg in config["checkers"]:
                if checker_cfg["class_name"] =="LabelGenerator":
                    checker_instance = initialize_checker(checker_cfg)
                    for method_cfg in checker_cfg["methods"]:
                        
                        if not method_cfg.get("enabled", True) or "method_name" not in method_cfg:
                            continue     
                        
                        if checker_instance.__class__.__name__ == "LabelGenerator":
                            method_name = method_cfg["method_name"]
                            method_to_call = getattr(checker_instance, method_name)
                            params = method_cfg.get("params", {})
                            
                            if method_name == "LT_difficulty":
                                model_answers,correct_score,processes,pass_rate = method_to_call(
                                    example["question"],
                                    example["RAG"],
                                    example["answer"], 
                                    **params)

                                for i,ans in enumerate(model_answers):
                                    answer_record = {
                                        'question': example["question"],
                                        'RAG': example["RAG"],
                                        'answer': example["answer"],
                                        '困难等级': round(1 - pass_rate, 2),
                                        'COT答案': ans,                                       
                                        '正确性得分': correct_score[i],
                                        '正确性过程': processes[i] if i < len(processes) else None
                                    }
                                    save_results(cot_path,fieldnames,answer_record)
                                        
        logger.info(f"lable and grade success! ")
        
                                    
        # 3. 处理所有检查器
        examples = load_data(config["cot_path"])
        logger.info(f"Loaded {len(examples)} cot examples")
        intermediate_path = config["intermediate_path"] 
        fieldnames = ['question', 'RAG', 'answer', '困难等级','COT答案',  '正确性得分', '正确性过程', '思考格式得分', '逻辑打分过程', '问答逻辑蕴含得分','句间逻辑支持得分', '自我反思得分', '答案格式得分']
        for example in examples:
            try:
                result = {
                    'question': example["question"],
                    'RAG': example["RAG"],
                    'answer': example["answer"],
                    '困难等级': example["困难等级"],
                    'COT答案': example["COT答案"],
                    '正确性得分': example["正确性得分"],
                    '正确性过程': example["正确性过程"]
                }
                
                # 处理所有评估器
                for checker_cfg in config["checkers"]:
                    if "class_name" not in checker_cfg or "methods" not in checker_cfg:
                        continue
                     
                    if checker_cfg["class_name"]=="Filter" or checker_cfg["class_name"]=="LabelGenerator" or checker_cfg["class_name"]=="CorrectnessChecker":
                        continue
                    
                    
                    # 初始化评估器
                    checker_instance = initialize_checker(checker_cfg)
                    
                    # 处理所有评估方法
                    for method_cfg in checker_cfg["methods"]:
                        if not method_cfg.get("enabled", True) or "method_name" not in method_cfg:
                            continue
                            
                        method_result = process_method(checker_instance, method_cfg, example)
                        result.update(method_result)

                    save_results(intermediate_path,fieldnames,result)
                
            except Exception as e:
                logger.error(f"Error processing example: {str(e)}")
                continue
        
        
        # 5. 过滤最优
        for filter_config in config["checkers"]:
            if filter_config["class_name"] =="Filter":
                filter_instance = initialize_checker(filter_config)       
                if intermediate_path:
                    output_path=config["output_csv"] 
                    intermediate_example=pd.read_csv(config["intermediate_path"])
            
                    for method_cfg in filter_config["methods"]:  
                        if not method_cfg.get("enabled", True) or "method_name" not in method_cfg:
                            continue     
                        if filter_instance.__class__.__name__ == "Filter":
                            method_name = method_cfg["method_name"]
                            method_to_call = getattr(filter_instance, method_name)
                            params = method_cfg.get("params", {})
                            method_result = method_to_call(intermediate_example,**params)
                            method_result.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        
        logger.info("Processing completed successfully")

    
    
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=False, default='/lustre/project-A/sourcecode/hongji/Fin_Cot_Eval/testpipeline/config.json',
                       help="Path to configuration JSON")
    args = parser.parse_args()
    
    main(args.config)