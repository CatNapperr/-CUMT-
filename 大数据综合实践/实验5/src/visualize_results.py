"""
结果可视化脚本
功能：1. 绘制训练曲线（step-loss & epoch-level）
      2. 加载最佳模型在验证集上预测，绘制混淆矩阵
"""
import os
import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from transformers import BertTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import MacBertClassifier
from dataset import TextClassificationDataset

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ========== 中文字体设置 ==========
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 类别名称
LABEL_NAMES = ['财经', '彩票', '房产', '股票', '家居', '教育',
               '科技', '社会', '时尚', '时政', '体育', '星座', '游戏', '娱乐']

# ========== 1. 绘制训练曲线 ==========
def plot_training_curves():
    """从5个epoch的result文件中读取step-loss并绘图"""
    result_dir = os.path.join(BASE_DIR, 'result')

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # --- 左图：每个epoch的step-loss曲线 ---
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0']
    epoch_labels = ['Epoch 1', 'Epoch 2', 'Epoch 3', 'Epoch 4', 'Epoch 5']

    epoch_avg_losses = []
    val_losses = []

    for epoch in range(1, 6):
        fname = f'MacBertClassifier_64_50_{epoch}_20260619_185825.txt'
        # Try alternative filenames for epochs 2-5
        alt_names = {
            2: 'MacBertClassifier_64_50_2_20260619_200943.txt',
            3: 'MacBertClassifier_64_50_3_20260619_212314.txt',
            4: 'MacBertClassifier_64_50_4_20260619_224124.txt',
            5: 'MacBertClassifier_64_50_5_20260619_235858.txt',
        }

        filepath = os.path.join(result_dir, fname)
        if not os.path.exists(filepath):
            filepath = os.path.join(result_dir, alt_names.get(epoch, ''))

        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping")
            continue

        df = pd.read_csv(filepath)

        steps = df[df['type'] == 'step']['step'].values
        losses = df[df['type'] == 'step']['loss'].values

        epoch_avg = df[df['type'] == 'epoch_avg_train']['loss'].values[0]
        val_loss = df[df['type'] == 'epoch_val']['loss'].values[0]
        epoch_avg_losses.append(epoch_avg)
        val_losses.append(val_loss)

        ax = axes[0]
        ax.plot(steps, losses, color=colors[epoch - 1], alpha=0.7,
                linewidth=0.8, label=f'{epoch_labels[epoch - 1]} (Avg: {epoch_avg:.4f})')

    axes[0].set_xlabel('Step', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('Training Loss per Step (Each Epoch)', fontsize=14)
    axes[0].legend(fontsize=9, loc='upper right')
    axes[0].grid(True, alpha=0.3)

    # --- 右图：epoch-level train loss & val loss ---
    epochs = range(1, len(epoch_avg_losses) + 1)
    ax2 = axes[1]
    ax2.plot(epochs, epoch_avg_losses, 'o-', color='#2196F3', linewidth=2,
             markersize=8, label='Train Loss (Epoch Avg)')
    ax2.plot(epochs, val_losses, 's--', color='#FF5722', linewidth=2,
             markersize=8, label='Val Loss')

    # 标注最佳epoch
    best_idx = np.argmin(val_losses)
    ax2.annotate(f'Best Epoch {epochs[best_idx]}\nVal Loss: {val_losses[best_idx]:.4f}',
                 xy=(epochs[best_idx], val_losses[best_idx]),
                 xytext=(epochs[best_idx] + 0.3, val_losses[best_idx] + 0.02),
                 fontsize=10, color='#FF5722',
                 arrowprops=dict(arrowstyle='->', color='#FF5722'))

    ax2.set_xlabel('Epoch', fontsize=12)
    ax2.set_ylabel('Loss', fontsize=12)
    ax2.set_title('Epoch-Level Training & Validation Loss', fontsize=14)
    ax2.set_xticks(epochs)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(BASE_DIR, 'docs', 'training_curves.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'训练曲线已保存: {save_path}')

    return epoch_avg_losses, val_losses


# ========== 2. 混淆矩阵 ==========
def plot_confusion_matrix():
    """加载最佳模型，在验证集上预测并绘制混淆矩阵"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # 加载验证集
    val_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'processed', 'val.csv'))
    with open(os.path.join(BASE_DIR, 'data', 'processed', 'label_mapping.json'),
              'r', encoding='utf-8') as f:
        mapping = json.load(f)
    mapping = {int(k): v for k, v in mapping.items()}
    label_names = [mapping[i] for i in range(len(mapping))]

    print(f'验证集: {len(val_df)} 条')

    # 加载tokenizer和模型
    pretrained_path = os.path.join(BASE_DIR, 'models', 'chinese-macbert-base')
    if not os.path.exists(os.path.join(pretrained_path, 'pytorch_model.bin')):
        pretrained_path = 'hfl/chinese-macbert-base'
    print(f'加载tokenizer: {pretrained_path}')
    tokenizer = BertTokenizer.from_pretrained(pretrained_path)

    model = MacBertClassifier(pretrained_model=pretrained_path, num_classes=14).to(device)
    checkpoint_path = os.path.join(BASE_DIR, 'checkpoints', 'MacBertClassifier_64_50_20260619_224122.pt')
    print(f'加载checkpoint: {checkpoint_path}')
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    print(f'Checkpoint Epoch {checkpoint["epoch"]}, Val Acc: {checkpoint["val_acc"]:.4f}')

    # 预测
    val_dataset = TextClassificationDataset(
        val_df['title'].tolist(),
        labels=val_df['label_id'].tolist(),
        tokenizer=tokenizer,
        max_len=64,
    )
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)

    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            logits = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # 计算混淆矩阵
    cm = confusion_matrix(all_labels, all_preds)

    # 绘制
    fig, ax = plt.subplots(figsize=(14, 12))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_names)
    disp.plot(ax=ax, cmap='Blues', colorbar=True, values_format='d')

    ax.set_title(f'Confusion Matrix on Validation Set (Epoch {checkpoint["epoch"]}, Acc={checkpoint["val_acc"]:.4f})',
                 fontsize=14, pad=20)
    ax.set_xlabel('Predicted Label', fontsize=12)
    ax.set_ylabel('True Label', fontsize=12)

    # 旋转标签
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
    plt.setp(ax.get_yticklabels(), fontsize=9)

    plt.tight_layout()
    save_path = os.path.join(BASE_DIR, 'docs', 'confusion_matrix.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'混淆矩阵已保存: {save_path}')

    # 输出每个类别的准确率
    print('\n各类别准确率:')
    cm_norm = cm.astype('float') / cm.sum(axis=1, keepdims=True)
    for i, name in enumerate(label_names):
        print(f'  {name}: {cm_norm[i, i]:.4f} ({cm[i, i]}/{cm[i].sum()})')


if __name__ == '__main__':
    print('=' * 60)
    print('1. 绘制训练曲线')
    print('=' * 60)
    epoch_avg, val_losses = plot_training_curves()
    print(f'\nEpoch avg train losses: {[f"{v:.4f}" for v in epoch_avg]}')
    print(f'Validation losses: {[f"{v:.4f}" for v in val_losses]}')

    print('\n' + '=' * 60)
    print('2. 绘制混淆矩阵')
    print('=' * 60)
    plot_confusion_matrix()
