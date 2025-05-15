import pandas as pd
from collections import Counter

class Filter:
    max_scores = {
        '思考格式得分': 8,
        '问答逻辑蕴含得分': 10,
        '句间逻辑支持得分': 10,
        '自我反思得分': 100,
        '正确性得分': 10,
        '答案格式得分': 8
    }

    def normalize_by_max(self, df):
        """按满分值比例归一化（0-1范围）"""
        df = df.copy()
        for col, max_val in self.max_scores.items():
            df[f'归一化_{col}'] = df[col] / max_val
        return df

    def calculate_composite_score(self, df, weights=None):
        """计算综合得分（可自定义权重）"""
        df = df.copy()
        normalized_cols = [f'归一化_{col}' for col in self.max_scores.keys()]
        
        if weights is None:
            weights = [1.0 / len(normalized_cols)] * len(normalized_cols)
        elif len(weights) != len(normalized_cols):
            raise ValueError("权重数量必须与评分项数量一致")
        
        df['综合得分'] = (df[normalized_cols] * weights).sum(axis=1)
        return df

    def select_top_per_question(self, df):
        """每组相同问题选出得分最高的一条"""
        best_indices = df.groupby('question')['综合得分'].idxmax()
        return df.loc[best_indices]

    def filter_data(self, df):
        return df[
            (df['困难等级'] >= 0.2) &
            (df['正确性得分'] >= 5) &
            (df['综合得分'] >= 0.5) &
            (df['RAG'] != '[]') &  
            (df['RAG'].str.strip() != '[]')
        ]

    def filter(self, df, weights=None):
        if weights is None:
            weights = [0.15, 0.1, 0.1, 0.01, 0.59, 0.05]
        
        df = self.normalize_by_max(df)
        df = self.calculate_composite_score(df, weights=weights)
        df = self.select_top_per_question(df)
        df = self.filter_data(df)
        return df