"""
模型模块
功能：MacBERT + 分类头的文本分类模型
"""
import torch.nn as nn
from transformers import BertModel
import os
# 设置环境变量，使用清华镜像站
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


class MacBertClassifier(nn.Module):
    """MacBERT 分类模型：预训练编码器 + Dropout + 全连接分类头"""

    def __init__(self, pretrained_model='hfl/chinese-macbert-base', num_classes=14):
        super().__init__()
        self.bert = BertModel.from_pretrained(pretrained_model)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        # MacBERT 编码
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # 取 last_hidden_state 的 [CLS] 向量（比 pooler_output 保留更多上下文）
        pooled = outputs.last_hidden_state[:, 0]
        # Dropout 正则化
        pooled = self.dropout(pooled)
        # 分类
        logits = self.classifier(pooled)
        return logits
