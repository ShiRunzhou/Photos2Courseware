#!/usr/bin/env python3
r"""
第二阶段：主题聚类

用法：
  python cluster.py --dir "D:\Photos\2024咖啡师培训"
  python cluster.py --dir "D:\Photos\2024咖啡师培训" --config config.yaml
  python cluster.py                                    # 交互式

功能：
  - 读取第一阶段提取的所有 JSON 文件
  - 按关键词匹配归入预设的知识模块
  - 输出聚类结果，保持照片拍摄顺序
"""

import os
import sys
import json
import glob
import argparse
import yaml
from collections import defaultdict

# ============================================================
# 配置加载
# ============================================================

def load_config(config_path: str) -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, config_path) if not os.path.isabs(config_path) else config_path
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


# ============================================================
# 聚类逻辑
# ============================================================

def classify_images(extracted_dir: str, modules: list) -> dict:
    """
    读取所有提取结果，按关键词归入模块。
    返回 { module_id: [result, ...], "_order": [(order, module_id, filename), ...] }
    """
    grouped = defaultdict(list)
    order_list = []

    # 读取所有 JSON（按文件名排序 = 拍摄顺序）
    json_files = sorted(glob.glob(os.path.join(extracted_dir, 'IMG_*.json')))
    if not json_files:
        print(f"错误: {extracted_dir} 中没有找到提取结果 JSON")
        sys.exit(1)

    print(f"读取 {len(json_files)} 个提取结果...")

    for fpath in json_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        text = data.get('extracted', {}).get('raw_text', '').lower()

        # 关键词匹配
        matched = None
        max_score = 0
        for mod in modules:
            score = 0
            for kw in mod['keywords']:
                if kw.lower() in text:
                    score += 1
            if score > max_score:
                max_score = score
                matched = mod['id']

        if max_score == 0:
            matched = 'Z_其他'

        grouped[matched].append(data)
        order_list.append((data['order'], matched, data['source']))

    return grouped, order_list


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='第二阶段：主题聚类')
    parser.add_argument('--dir', type=str, help='照片目录（提取结果在 {dir}/.workbuddy/extracted/）')
    parser.add_argument('--extracted', type=str, help='提取结果目录（直接指定）')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    args = parser.parse_args()

    # ----- 确定提取结果目录 -----
    if args.extracted:
        extracted_dir = args.extracted
    elif args.dir:
        extracted_dir = os.path.join(args.dir, '.workbuddy', 'extracted')
    else:
        # 交互模式
        print("=" * 50)
        print("  主题聚类工具")
        print("=" * 50)
        dir_input = input("请输入照片目录（提取结果在 {dir}/.workbuddy/extracted/）: ").strip().strip('"')
        if not dir_input:
            dir_input = input("或直接输入提取结果JSON所在目录: ").strip().strip('"')
        extracted_dir = os.path.join(dir_input, '.workbuddy', 'extracted') if os.path.isdir(dir_input) else dir_input

    if not os.path.isdir(extracted_dir):
        print(f"错误: 目录不存在: {extracted_dir}")
        sys.exit(1)

    # ----- 加载模块定义 -----
    yaml_config = load_config(args.config)
    if yaml_config and 'modules' in yaml_config:
        modules = yaml_config['modules']
        print(f"从 {args.config} 加载了 {len(modules)} 个模块定义")
    else:
        print("警告: 未找到配置文件中的模块定义，使用默认模块")
        modules = [
            {"id": "Z_其他", "label": "其他", "keywords": []}
        ]

    # ----- 执行聚类 -----
    print(f"提取结果目录: {extracted_dir}")
    print("-" * 50)

    grouped, order_list = classify_images(extracted_dir, modules)

    # ----- 输出结果 -----
    output_dir = os.path.dirname(extracted_dir)  # .workbuddy/
    output_path = os.path.join(output_dir, 'cluster_result.json')

    # 构建输出结构
    result = {
        "modules": {},
        "order": order_list,
        "summary": {}
    }

    for mod_id, items in sorted(grouped.items()):
        # 找模块 label
        label = mod_id
        for m in modules:
            if m['id'] == mod_id:
                label = m['label']
                break

        result["modules"][mod_id] = {
            "label": label,
            "count": len(items),
            "items": items
        }
        result["summary"][mod_id] = len(items)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ----- 打印摘要 -----
    print(f"\n聚类完成！输出: {output_path}")
    print(f"\n模块分布:")
    total = sum(result["summary"].values())
    for mod_id in sorted(result["summary"].keys()):
        label = result["modules"][mod_id]["label"]
        count = result["summary"][mod_id]
        bar = "█" * count
        print(f"  {mod_id:15s} [{label}] {count:2d}张 {bar}")

    print(f"\n总计: {total} 张 → {len(result['modules'])} 个模块")

    # 打印分配顺序（前20条）
    print(f"\n照片 → 模块 映射 (前20条):")
    for i, (order, mid, src) in enumerate(order_list[:20]):
        print(f"  {order:2d}. {src:35s} → {mid}")
    if len(order_list) > 20:
        print(f"  ... 共 {len(order_list)} 张")


if __name__ == '__main__':
    main()
