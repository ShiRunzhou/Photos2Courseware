#!/usr/bin/env python3
r"""
第一阶段：照片内容提取

用法：
  python batch_extract.py --dir "D:\Photos\2024咖啡师培训"
  python batch_extract.py --dir "D:\Photos\2024咖啡师培训" --mode two
  python batch_extract.py --dir "D:\Photos\2024咖啡师培训" --limit 5 --resume
  python batch_extract.py                  # 交互式：提示输入路径和模式
  python batch_extract.py --config config.yaml  # 从配置文件读取

核心参数：
  --dir PATH        照片文件夹路径
  --mode MODE       处理模式：single(单次调用) / two(两步调用)
  --config FILE     配置文件（默认 config.yaml）

其他：
  --limit N         只处理前 N 张
  --resume          跳过已有的
  --force           强制覆盖

设计原则：
  - 通用可复用：换照片目录即可用于新场景
  - 断点续传：已处理的照片自动跳过
  - 容错：单张失败不影响后续处理，输出错误日志
"""

import os
import sys
import json
import base64
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

import yaml
import requests


# ============================================================
# 配置加载
# ============================================================

def load_config(config_path: str) -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, config_path) if not os.path.isabs(config_path) else config_path

    if not os.path.exists(full_path):
        return None  # 没有配置文件时返回 None，由调用方处理

    with open(full_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


# ============================================================
# 模型调用
# ============================================================

def chat_with_vl(config: dict, prompt: str, image_b64: str = None, image_path: str = None) -> str:
    """调用 VL 模型"""
    vl = config['vl_model']

    if image_b64 is None and image_path:
        image_b64 = encode_image(image_path)

    content = [{"type": "text", "text": prompt}]
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
        })

    last_error = None
    for attempt in range(vl['max_retries'] + 1):
        try:
            headers = {"Content-Type": "application/json"}
            api_key = vl.get('api_key', '')
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.post(vl['endpoint'], json={
                "model": vl['model_name'],
                "messages": [{"role": "user", "content": content}]
            }, headers=headers, timeout=vl['timeout'])
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.Timeout:
            last_error = "请求超时"
        except requests.exceptions.ConnectionError:
            last_error = "连接失败"
        except Exception as e:
            last_error = str(e)

        if attempt < vl['max_retries']:
            delay = vl.get('retry_delay', 5) * (attempt + 1)
            print(f"      ⚠ {last_error}，{delay}秒后重试 ({attempt+1}/{vl['max_retries']})")
            time.sleep(delay)

    raise RuntimeError(f"调用失败（已重试{vl['max_retries']}次）: {last_error}")


def encode_image(path: str) -> str:
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


# ============================================================
# 内容类型解析
# ============================================================

VALID_TYPES = {'mindmap', 'text_slide', 'flowchart', 'table', 'material_photo', 'scene'}

def parse_single_pass_result(raw: str) -> dict:
    """解析单次调用返回的 [TYPE] + [CONTENT] 格式"""
    result = {
        "content_type": "text_slide",
        "raw_text": raw.strip()
    }

    # 尝试匹配 [TYPE]: xxx
    type_match = re.search(r'\[TYPE\]:\s*(\w+)', raw, re.IGNORECASE)
    if type_match:
        ct = type_match.group(1).lower().strip()
        if ct in VALID_TYPES:
            result["content_type"] = ct

    # 尝试提取 [CONTENT]: 后的内容
    content_match = re.search(r'\[CONTENT\]:\s*\n?(.*)', raw, re.DOTALL | re.IGNORECASE)
    if content_match:
        result["raw_text"] = content_match.group(1).strip()
    elif type_match:
        # 有类型标记但没有内容标记，把类型标记后的内容作为正文
        rest = raw[type_match.end():].strip()
        if rest:
            result["raw_text"] = rest

    return result


def detect_content_type(config: dict, image_b64: str) -> str:
    """两步模式：先判断内容类型"""
    ct_config = config['content_types']
    prompt = ct_config.get('detect_prompt',
        "判断照片内容类型，只回答: mindmap | text_slide | flowchart | table | material_photo | scene")

    result = chat_with_vl(config, prompt, image_b64)
    for ct in VALID_TYPES:
        if ct in result.lower():
            return ct
    return 'text_slide'


# ============================================================
# 单张处理
# ============================================================

def process_single(
    config: dict,
    image_path: str,
    order: int,
    max_order: int,
    two_pass: bool = False
) -> dict:
    """处理单张照片，返回结构化JSON"""
    filename = os.path.basename(image_path)
    image_b64 = encode_image(image_path)

    if two_pass:
        # 两步模式：先检测类型，再提取内容
        content_type = detect_content_type(config, image_b64)
        print(f"      → 类型: {content_type}")
        extract_prompts = config['content_types'].get('extract_prompts', {})
        prompt = extract_prompts.get(content_type, extract_prompts.get('text_slide', '提取所有文字'))
        extracted_text = chat_with_vl(config, prompt, image_b64)
    else:
        # 单次模式：一次调用同时检测和提取
        prompt = config['content_types'].get('detect_and_extract_prompt',
            "请判断照片类型并提取全部内容。先输出[TYPE]:类型标签，再输出[CONTENT]:提取内容。")
        raw_response = chat_with_vl(config, prompt, image_b64)
        parsed = parse_single_pass_result(raw_response)
        content_type = parsed["content_type"]
        extracted_text = parsed["raw_text"]
        print(f"      → 类型: {content_type}")

    return {
        "source": filename,
        "order": order,
        "content_type": content_type,
        "extracted": {
            "raw_text": extracted_text.strip()
        },
        "processed_at": datetime.now().isoformat()
    }


# ============================================================
# 默认配置（当没有 config.yaml 时使用）
# ============================================================

DEFAULT_CONFIG = {
    "vl_model": {
        "endpoint": "http://192.168.2.20:1234/v1/chat/completions",
        "model_name": "qwen/qwen3-vl-8b",
        "timeout": 300,
        "max_retries": 2,
        "retry_delay": 5,
    },
    "content_types": {
        "detect_and_extract_prompt": (
            "请严格按以下格式输出，先判断类型再提取内容：\n"
            "[TYPE]: <类型标签>\n"
            "[CONTENT]:\n"
            "<提取的全部内容>\n\n"
            "类型标签：mindmap(思维导图) | text_slide(PPT课件) | flowchart(流程图) "
            "| table(表格) | material_photo(纸质材料) | scene(实操场景)"
        ),
        "detect_prompt": (
            "判断照片内容类型，只回答以下标签之一：\n"
            "mindmap | text_slide | flowchart | table | material_photo | scene"
        ),
        "extract_prompts": {
            "mindmap":      "提取思维导图的完整层级结构，用嵌套列表输出，保留标题层级。",
            "text_slide":   "提取PPT全部文字，保持标题层级和列表序号。",
            "flowchart":     "提取流程图节点文字，用 → 表示流向关系。",
            "table":         "提取表格为Markdown格式，保留表头行列。",
            "material_photo":"描述内容并提取所有文字标签，按分类整理。",
            "scene":         "描述场景中的设备和动作，提取可见的标注文字。",
        }
    }
}


def build_config(config_path: str, args) -> dict:
    """
    构建运行配置。
    - 有 --dir / --mode 等参数 → 直接使用
    - 无任何参数（双击打开）→ 交互式输入
    """
    yaml_config = load_config(config_path)
    config = yaml_config if yaml_config else DEFAULT_CONFIG

    # 判断是否交互模式：没有传任何命令行参数
    interactive = (len(sys.argv) == 1)

    if interactive:
        print("=" * 50)
        print("  照片内容提取工具")
        print("=" * 50)

    # ----- 照片目录 -----
    if args.dir:
        photo_dir = args.dir
    elif interactive:
        # 交互模式：显示配置文件中的默认路径作为提示
        if yaml_config and 'scene' in yaml_config:
            default_dir = yaml_config['scene']['photo_dir']
        else:
            default_dir = ""
        if default_dir:
            print(f"\n配置文件中记录的照片目录: {default_dir}")
        user_input = input("请输入照片文件夹路径: ").strip().strip('"')
        photo_dir = user_input if user_input else default_dir
    elif yaml_config and 'scene' in yaml_config:
        photo_dir = yaml_config['scene']['photo_dir']
    else:
        photo_dir = input("请输入照片文件夹路径: ").strip().strip('"')

    if not photo_dir or not os.path.isdir(photo_dir):
        print(f"错误: 照片目录不存在: {photo_dir}")
        sys.exit(1)

    # ----- 输出目录 -----
    output_dir = os.path.join(photo_dir, '.workbuddy', 'extracted')

    # ----- 处理模式 -----
    if args.mode:
        two_pass = (args.mode == 'two')
    elif args.two_pass:
        two_pass = True
    elif interactive:
        print("\n处理模式:")
        print("  [1] 单次调用 — 一次API调用同时检测类型+提取（快，~23s/张）")
        print("  [2] 两步调用 — 先检测类型，再针对性提取（更精准）")
        choice = input("请选择 (1/2，默认1): ").strip()
        two_pass = (choice == '2')
    else:
        two_pass = False

    return {
        "photo_dir": photo_dir,
        "output_dir": output_dir,
        "two_pass": two_pass,
        "vl_model": config['vl_model'],
        "content_types": config['content_types'],
    }


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='照片内容提取 — 通用化批处理脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python batch_extract.py --dir "D:\\Photos\\2024咖啡师培训"
  python batch_extract.py --dir "D:\\Photos\\2024咖啡师培训" --mode two
  python batch_extract.py --dir "D:\\Photos\\2024咖啡师培训" --limit 5
  python batch_extract.py                                       # 交互式输入
        """
    )
    parser.add_argument('--dir', type=str, default=None,
                        help='照片文件夹路径（覆盖 config.yaml 中的设置）')
    parser.add_argument('--mode', type=str, default=None,
                        choices=['single', 'two'],
                        help='处理模式：single(单次调用) / two(两步调用)')
    parser.add_argument('--config', default='config.yaml',
                        help='配置文件路径（默认 config.yaml）')
    parser.add_argument('--two-pass', action='store_true',
                        help='[已弃用] 请使用 --mode two')
    parser.add_argument('--resume', action='store_true',
                        help='跳过已处理的照片（断点续传）')
    parser.add_argument('--limit', type=int, default=0,
                        help='只处理前 N 张（0=全部）')
    parser.add_argument('--force', action='store_true',
                        help='强制覆盖已有结果')
    args = parser.parse_args()

    # ----- 构建配置 -----
    config = build_config(args.config, args)
    photo_dir   = config['photo_dir']
    output_dir  = config['output_dir']
    two_pass    = config['two_pass']

    os.makedirs(output_dir, exist_ok=True)

    # ----- 扫描照片 -----
    images = sorted(Path(photo_dir).glob("*.jpg"))
    if not images:
        print(f"错误: {photo_dir} 中没有找到 .jpg 文件")
        sys.exit(1)

    if args.limit > 0:
        images = images[:args.limit]

    # ----- 断点续传检查 -----
    to_process = []
    skipped = 0
    for i, img in enumerate(images, 1):
        out_path = os.path.join(output_dir, f"{img.stem}.json")
        if os.path.exists(out_path):
            if args.force:
                os.remove(out_path)
                to_process.append((i, img, out_path))
            elif args.resume:
                skipped += 1
                continue
            else:
                skipped += 1
                continue
        else:
            to_process.append((i, img, out_path))

    if not to_process:
        print(f"所有 {skipped} 张照片已处理完毕。")
        print("使用 --force 强制重新处理，或 --limit N 处理前N张。")
        return

    # ----- 开始处理 -----
    vl = config['vl_model']
    print(f"{'='*60}")
    print(f"照片目录: {photo_dir}")
    print(f"输出目录: {output_dir}")
    print(f"模型: {vl['model_name']} @ {vl['endpoint']}")
    print(f"模式: {'两步调用（先检测再提取）' if two_pass else '单次调用（检测+提取合一）'}")
    print(f"总计: {len(images)} 张 | 待处理: {len(to_process)} | 跳过: {skipped}")
    print(f"{'='*60}")

    success = 0
    fail = 0
    start_time = time.time()

    for order, img, out_path in to_process:
        print(f"\n[{success+fail+1}/{len(to_process)}] {img.name} ", end='', flush=True)

        try:
            result = process_single(config, str(img), order, len(images), two_pass=two_pass)

            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"     ✓ 完成 ({len(result['extracted']['raw_text'])} 字符)")
            success += 1

        except Exception as e:
            print(f"\n     ✗ 失败: {e}")
            fail += 1

            error_result = {
                "source": img.name,
                "order": order,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
            error_path = out_path.replace('.json', '_error.json')
            with open(error_path, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)

    # ----- 汇总 -----
    elapsed = time.time() - start_time
    avg_time = elapsed / max(success, 1)

    print(f"\n{'='*60}")
    print(f"汇总: ✓ {success} 成功 | ✗ {fail} 失败 | 跳过 {skipped}")
    print(f"耗时: {elapsed:.0f}s (均 {avg_time:.0f}s/张)")
    print(f"输出: {output_dir}")

    summary = {
        "photo_dir": photo_dir,
        "model": vl['model_name'],
        "total": len(images),
        "processed": success,
        "failed": fail,
        "skipped": skipped,
        "mode": "two_pass" if two_pass else "single_pass",
        "elapsed_seconds": round(elapsed),
        "avg_seconds_per_image": round(avg_time, 1),
        "completed_at": datetime.now().isoformat()
    }
    summary_path = os.path.join(output_dir, '_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"汇总报告: {summary_path}")

    if fail > 0:
        print(f"\n⚠ 有 {fail} 张处理失败，检查 *_error.json 后使用 --resume 重新处理")


if __name__ == '__main__':
    main()
