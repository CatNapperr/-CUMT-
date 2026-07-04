"""
数据集模块
功能：将文本分词为 MacBERT 的输入格式，供 DataLoader 使用
"""
import torch
from torch.utils.data import Dataset


class TextClassificationDataset(Dataset):
    """文本分类数据集，使用 MacBERT tokenizer 将标题转为 input_ids"""

    def __init__(self, titles, labels=None, tokenizer=None, max_len=64):
        """
        Args:
            titles: 标题文本列表
            labels: 标签 ID 列表（测试集可为 None）
            tokenizer: MacBERT 的 tokenizer
            max_len: 最大序列长度
        """
        self.titles = titles
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.titles)

    def __getitem__(self, idx):
        title = str(self.titles[idx])
        # tokenizer 自动完成分词、padding、truncation
        encoding = self.tokenizer(
            title,
            truncation=True,
            padding='max_length',
            max_length=self.max_len,
            return_tensors='pt',
        )
        item = {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
        }
        if self.labels is not None:
            item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item
