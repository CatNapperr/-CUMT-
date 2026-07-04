"""
训练模块
功能：训练循环、验证评估、模型保存、日志记录
"""
import os
import logging
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import get_cosine_schedule_with_warmup
from torch.optim import AdamW
from tqdm import tqdm
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score, f1_score, classification_report


def setup_logger(log_path, name='train'):
    """设置 logger，同时输出到控制台和日志文件"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # 文件处理器
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def save_epoch_records(records, save_path):
    """将 epoch 内的 step-loss 记录保存为结构化数据文件（Excel可打开）"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write("step,loss,type\n")
        for entry in records:
            f.write(entry)


def train_one_epoch(model, dataloader, optimizer, scheduler, criterion, device,
                     epoch=1, record_step=50, result_dir='result',
                     model_name='model', batch_size=64):
    """
    训练一个 epoch
    - 每 record_step 步记录一次 step-loss 到 result/ 下的结构化数据文件
    - 返回: (avg_loss, record_file_path)
    """
    model.train()
    total_loss = 0
    progress = tqdm(dataloader, desc='Training')

    # 准备 result 数据文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_filename = f"{model_name}_{batch_size}_{record_step}_{epoch}_{timestamp}.txt"
    record_path = os.path.join(result_dir, record_filename)
    records = []

    total_batches = len(dataloader)

    for step, batch in enumerate(progress, 1):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()
        logits = model(input_ids, attention_mask)
        loss = criterion(logits, labels)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        progress.set_postfix({'loss': f'{loss.item():.4f}'})

        # 每 record_step 步记录一次
        if step % record_step == 0:
            records.append(f"{step},{loss.item():.4f},step\n")

    # epoch 平均 train loss
    avg_loss = total_loss / total_batches
    records.append(f"{total_batches},{avg_loss:.4f},epoch_avg_train\n")

    # 写入结构化数据文件
    save_epoch_records(records, record_path)

    return avg_loss, record_path


def evaluate(model, dataloader, criterion, device):
    """在验证集上评估模型"""
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Evaluating'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            total_loss += loss.item()

            preds = torch.argmax(logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average='macro')
    return avg_loss, accuracy, macro_f1, all_preds, all_labels


def train(model, train_dataset, val_dataset, label_names, device,
          batch_size=64, epochs=5, lr=2e-5, save_dir='checkpoints',
          record_step=50, result_dir='result', log_dir='logs',
          optimizer_fn=None, scheduler_fn=None,
          resume_epoch=0, num_workers=0):
    """
    完整训练流程
    - 训练日志 → logs/ 下的 .log 文件
    - step-loss 数据 → result/ 下的 .txt 文件
    Args:
        model: 任意 nn.Module，只需 forward(input_ids, attention_mask) -> logits
        record_step: 每 N 个 batch 记录一次 step-loss 到 result/
        optimizer_fn: (model, lr) -> optimizer
        scheduler_fn: (optimizer, total_steps) -> scheduler
    返回: 最佳模型 checkpoint 的路径
    """
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    model_name = model.__class__.__name__

    # 设置日志文件（logs/）
    log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f"{model_name}_{batch_size}_{record_step}_{log_timestamp}.log")
    logger = setup_logger(log_path)

    logger.info(f"设备: {device}")
    logger.info(f"模型: {model_name} | Batch Size: {batch_size} | Epochs: {epochs}")
    logger.info(f"学习率: {lr} | Record Step: {record_step}")
    logger.info(f"训练集: {len(train_dataset)} | 验证集: {len(val_dataset)} | 类别数: {len(label_names)}")
    logger.info(f"标签: {label_names}")

    # ---------- DataLoader ----------
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    # ---------- 标准交叉熵损失（无权重、无平滑）----------
    criterion = nn.CrossEntropyLoss()

    logger.info(f"Loss: CrossEntropyLoss（无权重、无平滑）")

    # ---------- 统一学习率 ----------
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in model.named_parameters()
                    if not any(nd in n for nd in no_decay)],
         'weight_decay': 1e-2},
        {'params': [p for n, p in model.named_parameters()
                    if any(nd in n for nd in no_decay)],
         'weight_decay': 0.0},
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=lr)

    # ---------- 余弦退火调度 ----------
    remaining_epochs = epochs - resume_epoch
    total_steps = len(train_loader) * remaining_epochs
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    logger.info(f"优化器: AdamW | 统一学习率: {lr}")
    logger.info(f"调度器: Cosine Decay | 剩余 {remaining_epochs} epoch / {total_steps} 步 | Warmup={warmup_steps}步")

    best_val_loss = float('inf')
    best_f1 = 0
    best_acc = 0
    patience_counter = 0

    start_epoch = resume_epoch + 1
    logger.info(f"起始 Epoch: {start_epoch} | 目标 Epoch: {epochs}")
    if resume_epoch > 0:
        logger.info(f"（从 Epoch {resume_epoch} 的 checkpoint 恢复训练）")

    for epoch in range(start_epoch, epochs + 1):
        logger.info(f"{'='*50}")
        logger.info(f"Epoch {epoch}/{epochs}")

        train_loss, record_path = train_one_epoch(
            model, train_loader, optimizer, scheduler, criterion, device,
            epoch=epoch, record_step=record_step, result_dir=result_dir,
            model_name=model_name, batch_size=batch_size,
        )

        val_loss, val_acc, val_f1, preds, labels = evaluate(model, val_loader, criterion, device)

        # 追加 Val Loss 到 result 数据文件
        with open(record_path, 'a', encoding='utf-8') as f:
            f.write(f"{len(train_loader)},{val_loss:.4f},epoch_val\n")

        logger.info(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        logger.info(f"Val Accuracy: {val_acc:.4f} | Val Macro F1: {val_f1:.4f}")
        logger.info(f"数据文件: {record_path}")
        

        # pt保存命名规范 - 时间戳归档 + best.pt 指针
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_name = f"{model_name}_{batch_size}_{record_step}_{timestamp}.pt"
        checkpoint_path = os.path.join(save_dir, checkpoint_name)
        best_ptr_path = os.path.join(save_dir, 'best.pt')

        # 保存最佳模型（基于 val loss，泛化性更好）
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_acc = val_acc
            best_f1 = val_f1
            patience_counter = 0
            # 保存时间戳归档文件
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
                'val_f1': val_f1,
            }, checkpoint_path)
            # 同时更新 best.pt 指针（覆盖）
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
                'val_f1': val_f1,
            }, best_ptr_path)
            logger.info(f"-> 新最佳模型保存 (Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, F1: {val_f1:.4f})")
            logger.info(f"   归档: {checkpoint_name}")
            logger.info(f"   指针: best.pt")
        else:
            patience_counter += 1
            logger.info(f"Val Loss 未提升 (已连续 {patience_counter} 轮)")

        if patience_counter >= 2:
            logger.info(f"验证集 Val Loss 连续 2 轮未降低，提前停止训练")
            break

    logger.info(f"{'='*50}")
    logger.info(f"训练完成！最佳 Val Loss: {best_val_loss:.4f}, 对应 Acc: {best_acc:.4f}, F1: {best_f1:.4f}")

    # 加载最佳模型（始终用 best.pt 指针），输出详细分类报告
    best_ptr_path = os.path.join(save_dir, 'best.pt')
    checkpoint = torch.load(best_ptr_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    _, _, _, preds, labels = evaluate(model, val_loader, criterion, device)
    logger.info(f"\n详细分类报告:\n{classification_report(labels, preds, target_names=label_names, digits=4)}")

    return best_ptr_path
