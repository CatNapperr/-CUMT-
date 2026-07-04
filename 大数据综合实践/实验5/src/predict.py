"""
预测模块
功能：加载训练好的模型，对测试集进行预测，输出 result.txt
"""
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm


def predict(model, test_dataset, label_mapping, device, batch_size=64):
    """对测试集进行批量预测"""
    model.eval()
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    all_preds = []

    with torch.no_grad():
        for batch in tqdm(test_loader, desc='Predicting'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)

            logits = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())

    # 将预测的 label_id 映射为类别名称
    results = [label_mapping[pid] for pid in all_preds]
    return results


def save_results(results, output_path):
    """将预测结果写入文件，每行一个类别"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for label in results:
            f.write(label + '\n')
    print(f'预测结果已保存至: {output_path}')
    print(f'总行数: {len(results)}')
