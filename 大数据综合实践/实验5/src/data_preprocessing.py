"""
数据预处理模块
功能：读取原始数据、分层采样划分训练/验证集、保存中间结果
"""
import os
import json
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


def load_train_data(data_path: str) -> pd.DataFrame:
    """读取训练集：标签ID\t标签\t标题"""
    df = pd.read_csv(
        data_path,
        sep='\t',
        header=None,
        names=['label_id', 'label', 'title'],
        encoding='utf-8'
    )
    # 清理标题首尾空白
    df['title'] = df['title'].str.strip()
    # 空标题用占位符填充
    df['title'] = df['title'].fillna('').replace('', '空标题')
    return df


def load_test_data(data_path: str) -> pd.DataFrame:
    """读取测试集：每行一个标题"""
    titles = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            titles.append(line.strip())
    return pd.DataFrame({'title': titles})


def split_data(df: pd.DataFrame, test_size=0.1, random_state=42):
    """
    分层采样划分训练集和验证集
    保证划分后各类别比例与原始分布一致
    """
    splitter = StratifiedShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train_idx, val_idx = next(splitter.split(df, df['label_id']))
    train_df = df.iloc[train_idx].reset_index(drop=True)
    val_df = df.iloc[val_idx].reset_index(drop=True)
    return train_df, val_df


def build_label_mapping(df: pd.DataFrame):
    """构建 label_id -> label_name 的映射（按 ID 排序确保顺序固定）"""
    mapping = (
        df[['label_id', 'label']]
        .drop_duplicates()
        .sort_values('label_id')
        .set_index('label_id')['label']
        .to_dict()
    )
    return mapping


def save_data(train_df, val_df, test_df, label_mapping, output_dir):
    """将划分后的数据保存到本地"""
    os.makedirs(output_dir, exist_ok=True)

    train_df.to_csv(os.path.join(output_dir, 'train.csv'), index=False, encoding='utf-8')
    val_df.to_csv(os.path.join(output_dir, 'val.csv'), index=False, encoding='utf-8')
    test_df.to_csv(os.path.join(output_dir, 'test.csv'), index=False, encoding='utf-8')

    with open(os.path.join(output_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
        json.dump(label_mapping, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_dir}")
    print(f"  train.csv: {len(train_df)} 条")
    print(f"  val.csv:   {len(val_df)} 条")
    print(f"  test.csv:  {len(test_df)} 条")


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_path = os.path.join(base_dir, 'data', 'train.txt')
    test_path = os.path.join(base_dir, 'data', 'test.txt')
    output_dir = os.path.join(base_dir, 'data', 'processed')

    train_full = load_train_data(train_path)
    test_df = load_test_data(test_path)

    print(f"训练集总样本数: {len(train_full)}")
    print(f"测试集样本数: {len(test_df)}")
    print(f"类别数: {train_full['label_id'].nunique()}")
    print("\n各类别分布:")
    print(train_full['label'].value_counts())

    train_df, val_df = split_data(train_full)
    print(f"\n划分后训练集: {len(train_df)}, 验证集: {len(val_df)}")

    mapping = build_label_mapping(train_full)
    print(f"\n标签映射: {mapping}")

    # 保存到本地
    save_data(train_df, val_df, test_df, mapping, output_dir)
