import pandas as pd
import json
import argparse
import os
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

def initialize_checkers(checker_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """初始化所有检查器实例"""
    checkers = {}
    for checker_cfg in checker_configs:
        class_name = checker_cfg["class_name"]
        module_name = f"checkers.{class_name.lower()}"
        try:
            module = importlib.import_module(module_name)
            CheckerClass = getattr(module, class_name)
            checkers[class_name] = CheckerClass()
        except Exception as e:
            logger.error(f"Failed to initialize {class_name}: {str(e)}")
            raise
    return checkers

def run_evaluation_pipeline(checkers: Dict[str, Any], row: pd.Series, attempts: int, threshold: float) -> Dict[str, Any]:
    """执行完整的评估流程"""
    # 1. 运行难度评估和答案生成
    model_answers, c_score, pass_rate = checkers["LabelGenerator"].run_newlabel(
        select_question=row['question'],
        select_passage=row['RAG'],
        attempts=attempts,
        reference_answer=row['answer']
    )
    
    results = []
    for i, ans in enumerate(model_answers):
        # 2. 评估思考格式
        think_format_score = checkers["FormatChecker"].run_evaluate_format(ans, threshold)
        
        # 3. 评估逻辑思维
        logic_thinking, logic_fav_score, logic_ent_score = checkers["LogicChecker"].run_evaluate_logic(ans)
        
        # 4. 评估自我反思
        reflect_score = checkers["ReflectionChecker"].run_evaluate_reflection(ans)
        
        # 5. 评估答案格式
        stripped_answer, answer_format_score = checkers["FormatChecker"].run_evaluate_format(ans)
        
        # 6. 评估正确性
        correct_score = checkers["CorrectnessChecker"].run_evaluate_correctness(stripped_answer, row['answer'])
        
        # 组装结果
        score = {
            '问题': row['question'],
            'RAG': row['RAG'],
            '参考答案': row['answer'],
            '答案推理过程': ans,
            '困难程度(0-1,简单-困难)': round(1 - pass_rate, 2),
            '思考格式得分': think_format_score,
            '逻辑打分过程': logic_thinking,
            '问答逻辑蕴含得分': logic_ent_score,
            '句间逻辑支持得分': logic_fav_score,
            '自我反思得分': reflect_score,
            '答案格式得分': answer_format_score,
            '正确性得分': correct_score
        }
        results.append(score)
    
    return results

def main(config_path: str, attempts: int = 3, threshold: float = 0.5) -> None:
    """主执行函数"""
    try:
        # 1. 加载配置
        config = load_config(config_path)
        logger.info(f"Loaded config from {config_path}")
        
        # 2. 初始化检查器
        checkers = initialize_checkers(config["checkers"])
        
        # 3. 加载数据
        df = pd.read_excel(config["data_path"]) if config["data_path"].endswith('.xlsx') else pd.read_csv(config["data_path"])
        logger.info(f"Loaded {len(df)} records from {config['data_path']}")
        
        # 4. 处理每条记录
        all_results = []
        for index, row in df.iterrows():
            try:
                results = run_evaluation_pipeline(checkers, row, attempts, threshold)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                continue
        
        # 5. 保存结果
        output_path = os.path.join(os.path.dirname(config["data_path"]), "evaluation_results.xlsx")
        pd.DataFrame(all_results).to_excel(output_path, index=False)
        logger.info(f"Evaluation completed. Results saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path to configuration JSON")
    parser.add_argument("--attempts", type=int, default=3, help="Number of attempts for answer generation")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold for format evaluation")
    args = parser.parse_args()
    
    main(args.config, args.attempts, args.threshold)