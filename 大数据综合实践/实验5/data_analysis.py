"""
数据分析脚本：多进程加速版
使用 multiprocessing 并行分词，大幅提升速度
"""
import os, json, math, re, time
from collections import Counter
from multiprocessing import Pool, cpu_count
import jieba

os.makedirs('docs', exist_ok=True)

# ==================== 分词相关函数 ====================
def clean_and_segment(text):
    """清洗并分词"""
    clean = re.sub(r'[（）()\[\]【】{}《》""\'\'、：；。，！？\-\—\~\s+★…·◆▶◀●◎■□▲△▼▽◆◇○◎☆★°′″℃＄％‰＠＆＃＊｜]+', ' ', text)
    words = jieba.lcut(clean)
    return [w for w in words if len(w.strip()) > 1 and not re.match(r'^[\d\s\.\+\-\*/%=,;:!\?@#\$&\(\)\（\）]+$', w)]

def get_chars(text):
    return [c for c in text if '一' <= c <= '鿿']

def batch_segment(titles_batch):
    return [clean_and_segment(t) for t in titles_batch]

def batch_extract_chars(titles_batch):
    return [get_chars(t) for t in titles_batch]

def chunk_list(lst, n):
    size = max(1, len(lst) // n)
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def calc_char_freq(titles_chunk):
    c = Counter()
    for t in titles_chunk:
        for ch in t:
            if '一' <= ch <= '鿿':
                c[ch] += 1
    return c

def calc_cat_words(args):
    titles_chunk, labels_chunk, all_cats = args
    counters = {cat: Counter() for cat in all_cats}
    for title, label in zip(titles_chunk, labels_chunk):
        words = clean_and_segment(title)
        counters[label].update(words)
    return counters

# ==================== 统计函数 ====================
def basic_stats(titles, word_counter, name):
    lengths = [len(t) for t in titles]
    mean_len = sum(lengths) / len(lengths)
    std_len = (sum((l - mean_len)**2 for l in lengths) / len(lengths))**0.5
    total_words = sum(word_counter.values())
    unique_words = len(word_counter)
    return {
        'name': name, 'count': len(titles),
        'avg_len': round(mean_len, 2), 'std_len': round(std_len, 2),
        'median_len': sorted(lengths)[len(lengths)//2],
        'min_len': min(lengths), 'max_len': max(lengths),
        'total_words': total_words, 'unique_words': unique_words,
        'avg_words': round(total_words / len(titles), 2),
        'lexical_diversity': round(unique_words / total_words * 100, 2),
    }

def calc_len_dist(titles):
    dist = {}
    for lo in range(0, 60, 5):
        hi = lo + 5
        cnt = sum(1 for t in titles if lo <= len(t) < hi)
        if cnt > 0:
            dist[f'{lo}-{hi}'] = cnt
    cnt = sum(1 for t in titles if len(t) >= 60)
    if cnt: dist['60+'] = cnt
    return dist

def js_divergence(p, q):
    m = {}
    for k in set(p.keys()) | set(q.keys()):
        pk, qk = p.get(k, 0), q.get(k, 0)
        mk = (pk + qk) / 2
        if mk > 0: m[k] = mk
    kl_pm = sum(p[k] * math.log2(p[k]/m[k]) for k in m if p.get(k, 0) > 0 and m[k] > 0)
    kl_qm = sum(q[k] * math.log2(q[k]/m[k]) for k in m if q.get(k, 0) > 0 and m[k] > 0)
    return (kl_pm + kl_qm) / 2

# ==================== 报告生成 ====================
def write_report(stats, other_stats, name, other_name,
                 word_counter, char_counter, cat_counter,
                 other_cat_counter, cat_word_counters,
                 train_dom, test_dom, jsd,
                 len_dist, other_char_counter,
                 train_cat_counter, test_cat_counter, all_cats, path):
    lines = []
    lines.append(f'# {name}数据分析报告\n')
    lines.append('## 1. 基本统计\n')
    lines.append(f'- 总样本数: {stats["count"]:,}')
    lines.append(f'- 总词数（jieba分词）: {stats["total_words"]:,}')
    lines.append(f'- 唯一词数: {stats["unique_words"]:,}')
    lines.append(f'- 每标题平均词数: {stats["avg_words"]}')
    lines.append(f'- 词汇丰富度（Type-Token Ratio）: {stats["lexical_diversity"]}%')
    lines.append(f'- 唯一汉字数: {len(char_counter):,}\n')

    lines.append('## 2. 标题长度分布\n')
    lines.append(f'- 最短: {stats["min_len"]} 字符 | 最长: {stats["max_len"]} 字符')
    lines.append(f'- 平均长度: {stats["avg_len"]} 字符 | 中位数: {stats["median_len"]} | 标准差: {stats["std_len"]}\n')
    lines.append('| 长度区间 | 数量 | 占比 |')
    lines.append('|---------|------|------|')
    for r, cnt in len_dist.items():
        lines.append(f'| {r} | {cnt} | {cnt/stats["count"]*100:.1f}% |')
    lines.append('')

    lines.append('## 3. 类别分布\n')
    lines.append('| 类别 | 数量 | 占比 |')
    lines.append('|------|------|------|')
    for cat, cnt in cat_counter.most_common():
        lines.append(f'| {cat} | {cnt:,} | {cnt/stats["count"]*100:.2f}% |')
    lines.append('')

    lines.append('## 4. 高频词汇 Top 50\n')
    lines.append('| 排名 | 词 | 频次 |')
    lines.append('|------|------|------|')
    for i, (word, freq) in enumerate(word_counter.most_common(50), 1):
        lines.append(f'| {i} | {word} | {freq:,} |')
    lines.append('')

    lines.append('## 5. 高频汉字 Top 30\n')
    lines.append('| 排名 | 字 | 频次 |')
    lines.append('|------|------|------|')
    for i, (ch, freq) in enumerate(char_counter.most_common(30), 1):
        lines.append(f'| {i} | {ch} | {freq:,} |')
    lines.append('')

    lines.append('## 6. 各类别高频词 Top 20\n')
    for cat in sorted(cat_word_counters.keys()):
        words = cat_word_counters[cat]
        lines.append(f'### {cat}\n')
        lines.append('| 排名 | 词 | 频次 |')
        lines.append('|------|------|------|')
        for i, (w, f) in enumerate(words.most_common(20), 1):
            lines.append(f'| {i} | {w} | {f:,} |')
        lines.append('')

    lines.append(f'## 7. 与{other_name}的对比分析\n')
    lines.append(f'### 7.1 基本规模对比\n')
    lines.append(f'| 指标 | {name} | {other_name} |')
    lines.append(f'|------|--------|------------|')
    lines.append(f'| 样本数 | {stats["count"]:,} | {other_stats["count"]:,} |')
    lines.append(f'| 平均标题长度(字符) | {stats["avg_len"]} | {other_stats["avg_len"]} |')
    lines.append(f'| 平均词数 | {stats["avg_words"]} | {other_stats["avg_words"]} |')
    lines.append(f'| 词汇丰富度 | {stats["lexical_diversity"]}% | {other_stats["lexical_diversity"]}% |')
    lines.append(f'| 唯一汉字数 | {len(char_counter):,} | {len(other_char_counter):,} |\n')

    lines.append(f'### 7.2 词分布相似度\n')
    lines.append(f'两个数据集词分布的 **Jensen-Shannon 散度**: {jsd:.4f}')
    lines.append('JS散度越接近0表示分布越相似，通常在0~1之间。\n')

    lines.append('### 7.3 类别分布对比\n')
    lines.append('| 类别 | 训练集数量 | 训练集占比 | 测试集数量 | 测试集占比 | 差异 |')
    lines.append('|------|-----------|-----------|-----------|-----------|------|')
    for cat in sorted(all_cats):
        tc = train_cat_counter.get(cat, 0)
        tec = test_cat_counter.get(cat, 0)
        tp = tc / 752476 * 100
        ep = tec / 83599 * 100
        lines.append(f'| {cat} | {tc:,} | {tp:.1f}% | {tec:,} | {ep:.1f}% | {abs(tp-ep):.1f}% |')
    lines.append('')

    lines.append(f'### 7.4 {name}更突出的词 (Top 20)\n')
    lines.append('| 词 | 本集(每百万词) | 对比集(每百万词) | 倍率 |')
    lines.append('|------|--------------|----------------|------|')
    dom = train_dom if name == '训练集' else test_dom
    for i, (w, v) in enumerate(list(dom.items())[:20], 1):
        tf_key = 'train_freq' if name == '训练集' else 'test_freq'
        of_key = 'test_freq' if name == '训练集' else 'train_freq'
        lines.append(f'| {w} | {v[tf_key]} | {v[of_key]} | {v["ratio"]}x |')
    lines.append('')

    lines.append(f'### 7.5 {other_name}更突出的词 (Top 20)\n')
    lines.append('| 词 | 本集(每百万词) | 对比集(每百万词) | 倍率 |')
    lines.append('|------|--------------|----------------|------|')
    dom2 = test_dom if name == '训练集' else train_dom
    for i, (w, v) in enumerate(list(dom2.items())[:20], 1):
        tf_key = 'test_freq' if name == '训练集' else 'train_freq'
        of_key = 'train_freq' if name == '训练集' else 'test_freq'
        lines.append(f'| {w} | {v[tf_key]} | {v[of_key]} | {v["ratio"]}x |')
    lines.append('')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'报告已保存: {path}')


# ==================== 主流程 ====================
if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    NCORES = min(cpu_count(), 8)
    print(f'CPU核心数: {cpu_count()} → 使用: {NCORES}')

    # ---------- 加载数据 ----------
    print('加载数据...')
    t_start = time.time()

    train_labels = []
    train_titles = []
    with open('data/train.txt', 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                train_labels.append(parts[1])
                train_titles.append(parts[2])

    test_titles = []
    with open('data/test.txt', 'r', encoding='utf-8') as f:
        test_titles = [line.strip() for line in f.readlines()]

    with open('result_file/88.445/result.txt', 'r', encoding='utf-8') as f:
        test_pred_labels = [line.strip() for line in f.readlines()]

    print(f'训练集: {len(train_titles):,} 条 | 测试集: {len(test_titles):,} 条')
    print(f'加载耗时: {time.time()-t_start:.1f}s')

    # 预加载自定义词
    for w in ['上证50ETF', 'ETF', '基金经理', '保本基金']:
        jieba.add_word(w)

    # ---------- 并行分词 ----------
    print(f'\n并行分词 (NCORES={NCORES})...')
    t_seg = time.time()

    train_chunks = list(chunk_list(train_titles, NCORES * 2))
    with Pool(NCORES) as p:
        train_word_results = p.map(batch_segment, train_chunks)
    train_all_words = [w for chunk in train_word_results for title_words in chunk for w in title_words]
    train_word_counter = Counter(train_all_words)

    test_chunks = list(chunk_list(test_titles, NCORES * 2))
    with Pool(NCORES) as p:
        test_word_results = p.map(batch_segment, test_chunks)
    test_all_words = [w for chunk in test_word_results for title_words in chunk for w in title_words]
    test_word_counter = Counter(test_all_words)

    print(f'分词耗时: {time.time()-t_seg:.1f}s')
    print(f'训练集总词数: {len(train_all_words):,} | 唯一词数: {len(train_word_counter):,}')
    print(f'测试集总词数: {len(test_all_words):,} | 唯一词数: {len(test_word_counter):,}')

    # ---------- 基础统计 ----------
    train_stats = basic_stats(train_titles, train_word_counter, '训练集')
    test_stats = basic_stats(test_titles, test_word_counter, '测试集')

    # ---------- 字符统计 ----------
    print('\n统计字符分布...')
    char_chunks = list(chunk_list(train_titles, NCORES * 4))
    with Pool(NCORES) as p:
        train_char_results = p.map(calc_char_freq, char_chunks)
    train_char_counter = Counter()
    for c in train_char_results:
        train_char_counter.update(c)

    char_chunks = list(chunk_list(test_titles, NCORES * 4))
    with Pool(NCORES) as p:
        test_char_results = p.map(calc_char_freq, char_chunks)
    test_char_counter = Counter()
    for c in test_char_results:
        test_char_counter.update(c)
    print(f'训练集唯一汉字: {len(train_char_counter):,} | 测试集唯一汉字: {len(test_char_counter):,}')

    # ---------- 类别分布 ----------
    train_cat_counter = Counter(train_labels)
    test_cat_counter = Counter(test_pred_labels)
    all_cats = sorted(set(list(train_cat_counter.keys()) + list(test_cat_counter.keys())))

    # ---------- 各类别词频 ----------
    print('\n统计各类别高频词...')
    cat_word_counters = {cat: Counter() for cat in all_cats}

    label_pairs = list(zip(train_titles, train_labels))
    cat_chunks = []
    for _chunk in chunk_list(label_pairs, NCORES * 2):
        t = [p[0] for p in _chunk]
        l = [p[1] for p in _chunk]
        cat_chunks.append((t, l, all_cats))

    with Pool(NCORES) as p:
        cat_results = p.map(calc_cat_words, cat_chunks)
    for result in cat_results:
        for cat in all_cats:
            cat_word_counters[cat].update(result[cat])

    # ---------- 词分布差异 ----------
    print('计算词分布差异...')
    train_total = sum(train_word_counter.values())
    test_total = sum(test_word_counter.values())
    all_top_words = set(w for w, _ in train_word_counter.most_common(5000)) | \
                    set(w for w, _ in test_word_counter.most_common(5000))

    train_prob = {w: train_word_counter.get(w, 0)/train_total for w in all_top_words}
    test_prob = {w: test_word_counter.get(w, 0)/test_total for w in all_top_words}
    jsd = js_divergence(train_prob, test_prob)

    word_diffs = {}
    for w in all_top_words:
        tf = train_word_counter.get(w, 0) / train_total * 1e6
        tef = test_word_counter.get(w, 0) / test_total * 1e6
        if max(tf, tef) > 3 and min(tf, tef) > 0:
            ratio = max(tf, tef) / min(tf, tef)
            if ratio > 2:
                word_diffs[w] = {'train_freq': round(tf, 2), 'test_freq': round(tef, 2), 'ratio': round(ratio, 1)}

    train_dominant_words = {w: v for w, v in sorted(word_diffs.items(), key=lambda x: -x[1]['train_freq'])
                            if v['train_freq'] > v['test_freq']}
    test_dominant_words = {w: v for w, v in sorted(word_diffs.items(), key=lambda x: -x[1]['test_freq'])
                           if v['test_freq'] > v['train_freq']}

    # ---------- 长度分布 ----------
    train_len_dist = calc_len_dist(train_titles)
    test_len_dist = calc_len_dist(test_titles)

    # ---------- 生成报告 ----------
    print('\n生成报告...')

    write_report(train_stats, test_stats, '训练集', '测试集',
                 train_word_counter, train_char_counter, train_cat_counter,
                 test_cat_counter, cat_word_counters,
                 train_dominant_words, test_dominant_words, jsd,
                 train_len_dist, test_char_counter,
                 train_cat_counter, test_cat_counter, all_cats,
                 'docs/训练集数据分析报告.md')

    write_report(test_stats, train_stats, '测试集', '训练集',
                 test_word_counter, test_char_counter, test_cat_counter,
                 train_cat_counter, cat_word_counters,
                 train_dominant_words, test_dominant_words, jsd,
                 test_len_dist, train_char_counter,
                 train_cat_counter, test_cat_counter, all_cats,
                 'docs/测试集数据分析报告.md')

    print(f'\n全部完成！总耗时: {time.time()-t_start:.1f}s')
