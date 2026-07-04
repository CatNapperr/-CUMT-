"""
主入口脚本
功能：整合数据预处理、模型训练、预测全流程
用法：
  python main.py --do_train --do_predict   # 训练 + 预测
  python main.py --do_predict              # 仅预测（需已有 checkpoint）
"""
import os
# 必须在 import transformers 之前设置镜像源
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import argparse
import json
import torch
import pandas as pd
from transformers import BertTokenizer

from data_preprocessing import load_train_data, load_test_data, split_data, build_label_mapping, save_data
from dataset import TextClassificationDataset
from model import MacBertClassifier
from train import train
from predict import predict, save_results


def get_local_model_path(base_dir):
    """返回本地模型路径，如果存在则优先使用本地"""
    local_path = os.path.join(base_dir, 'models', 'chinese-macbert-base')
    if os.path.exists(os.path.join(local_path, 'pytorch_model.bin')):
        return local_path
    return None


def main():
    parser = argparse.ArgumentParser(description='MacBERT 文本分类')
    parser.add_argument('--do_train', action='store_true', help='是否训练模型')
    parser.add_argument('--do_predict', action='store_true', help='是否预测测试集')
    parser.add_argument('--batch_size', type=int, default=64, help='batch size')
    parser.add_argument('--epochs', type=int, default=5, help='训练轮数')
    parser.add_argument('--lr', type=float, default=2e-5, help='学习率')
    parser.add_argument('--max_len', type=int, default=64, help='最大序列长度')
    parser.add_argument('--num_workers', type=int, default=0, help='DataLoader 子进程数（Windows 建议 0，Linux 可设 2~4）')
    parser.add_argument('--record_step', type=int, default=50, help='每 N 个 batch 记录一次 step-loss 到 result/')
    parser.add_argument('--pretrained', type=str, default=None, help='预训练模型名称或路径')
    parser.add_argument('--checkpoint', type=str, default='checkpoints/best.pt', help='模型 checkpoint 路径')
    parser.add_argument('--resume', type=str, default=None, help='从指定 checkpoint 恢复训练（如 checkpoints/best.pt）')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 确定模型路径：优先本地，其次参数指定，最后 huggingface 在线
    if args.pretrained is None:
        local_model = get_local_model_path(base_dir)
        if local_model:
            args.pretrained = local_model
            print(f'使用本地模型: {local_model}')
        else:
            args.pretrained = 'hfl/chinese-macbert-base'
            print(f'使用在线模型: {args.pretrained}')
    else:
        print(f'使用指定模型: {args.pretrained}')

    # ---------- 数据准备 ----------
    processed_dir = os.path.join(base_dir, 'data', 'processed')
    if not os.path.exists(processed_dir):
        print('预处理数据不存在，重新执行数据划分...')
        train_path = os.path.join(base_dir, 'data', 'train.txt')
        test_path = os.path.join(base_dir, 'data', 'test.txt')

        train_full = load_train_data(train_path)
        test_df = load_test_data(test_path)
        train_df, val_df = split_data(train_full)
        mapping = build_label_mapping(train_full)
        save_data(train_df, val_df, test_df, mapping, processed_dir)
    else:
        train_df = pd.read_csv(os.path.join(processed_dir, 'train.csv'))
        val_df = pd.read_csv(os.path.join(processed_dir, 'val.csv'))
        test_df = pd.read_csv(os.path.join(processed_dir, 'test.csv'))
        with open(os.path.join(processed_dir, 'label_mapping.json'), 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        mapping = {int(k): v for k, v in mapping.items()}

    num_classes = len(mapping)
    id_to_label = mapping
    label_to_id = {v: k for k, v in id_to_label.items()}
    label_names = [id_to_label[i] for i in range(num_classes)]

    print(f'训练集: {len(train_df)} | 验证集: {len(val_df)} | 测试集: {len(test_df)}')
    print(f'类别数: {num_classes}')
    print(f'标签: {label_names}')

    # ---------- Tokenizer ----------
    print(f'加载 tokenizer: {args.pretrained}')
    tokenizer = BertTokenizer.from_pretrained(args.pretrained)

    # ---------- Dataset ----------
    train_dataset = TextClassificationDataset(
        train_df['title'].tolist(),
        labels=train_df['label_id'].tolist(),
        tokenizer=tokenizer,
        max_len=args.max_len,
    )
    val_dataset = TextClassificationDataset(
        val_df['title'].tolist(),
        labels=val_df['label_id'].tolist(),
        tokenizer=tokenizer,
        max_len=args.max_len,
    )
    test_dataset = TextClassificationDataset(
        test_df['title'].tolist(),
        labels=None,
        tokenizer=tokenizer,
        max_len=args.max_len,
    )

    # ---------- 训练 ----------
    if args.do_train:
        resume_epoch = 0
        if args.resume:
            print(f'恢复训练: {args.resume}')
            resume_data = torch.load(args.resume, map_location=device)
            resume_epoch = resume_data['epoch']
            print(f'  从 Epoch {resume_epoch} 恢复，Val Loss: {resume_data.get("val_loss", "N/A"):.4f}')

        print('\n初始化 MacBERT 分类模型...')
        model = MacBertClassifier(
            pretrained_model=args.pretrained,
            num_classes=num_classes
        ).to(device)

        if args.resume:
            model.load_state_dict(resume_data['model_state_dict'])
            print(f'  模型权重已加载')
            del resume_data

        checkpoint_path = train(
            model=model,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            label_names=label_names,
            device=device,
            batch_size=args.batch_size,
            epochs=args.epochs,
            lr=args.lr,
            record_step=args.record_step,
            num_workers=args.num_workers,
            result_dir=os.path.join(base_dir, 'result'),
            log_dir=os.path.join(base_dir, 'logs'),
            save_dir=os.path.join(base_dir, 'checkpoints'),
            resume_epoch=resume_epoch,
        )
        print(f'最佳模型保存至: {checkpoint_path}')

    # ---------- 预测 ----------
    if args.do_predict:
        print('\n加载模型进行预测...')
        checkpoint_path = os.path.join(base_dir, args.checkpoint)
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f'Checkpoint 不存在: {checkpoint_path}')

        model = MacBertClassifier(
            pretrained_model=args.pretrained,
            num_classes=num_classes
        ).to(device)

        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f'加载 checkpoint 成功 (Epoch {checkpoint["epoch"]}, Acc: {checkpoint["val_acc"]:.4f})')

        results = predict(model, test_dataset, id_to_label, device, batch_size=args.batch_size)
        save_results(results, os.path.join(base_dir, 'result.txt'))


if __name__ == '__main__':
    main()
