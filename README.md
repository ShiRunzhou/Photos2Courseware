# Photos2Courseware — 照片转培训课件

将培训现场照片（PPT投影、纸质材料、实操记录）自动转化为结构化讲义和教学PPT。

## 环境准备（一次性）

```bash
pip install -r requirements.txt                  # Python 依赖
npm install -g @marp-team/marp-cli               # PPT 渲染引擎
```
编辑 `config.yaml` 中的 `vl_model` 部分（本地模型留空 `api_key`，云端模型填写）：
```yaml
vl_model:
  endpoint: "http://192.168.2.20:1234/v1/chat/completions"
  model_name: "qwen/qwen3-vl-8b"
  api_key: ""        # 本地留空；云端填写 "sk-xxxxxx"
```

## 使用（最简单的方式）

**把整个项目和照片路径交给 AI agent，一句话搞定：**

> 请读取 `Photos2Courseware/scripts/run_all.md` 并执行全部任务。
> 照片目录：`D:\我的培训照片`

Agent 会自动完成：图像识别 → 主题分类 → 框架补全 → 讲义生成 → 幻灯片生成 → PPTX 渲染 → 产出复制。

**需要提前确认的只有一件事：** config.yaml 中的 VL 模型地址是否正确（`vl_model.endpoint`）。

## 产出

```
照片目录\output\
├── A_模块名.md        ← 讲义
├── B_模块名.md
├── A_模块名.pptx      ← 课件
└── B_模块名.pptx
```

## 如果只跑部分步骤

| 阶段 | 脚本 / Prompt |
|:---:|------|
| 一 图像提取 | `python scripts/batch_extract.py --dir "照片目录"` |
| 二 自动分模块 | 「请执行 scripts/run_all.md 步骤 2」 |
| 二 聚类 | `python scripts/cluster.py --dir "照片目录"` |
| 三 框架补全 | 「请执行 phase3_gap_analysis.md」 |
| 四 讲义生成 | 「请执行 phase4_lecture_notes.md」 |
| 五 幻灯片 | 「请执行 phase5_marp_slides.md」 |

## 目录结构

```
Photos2Courseware/
├── 使用说明.docx                 ← 电脑小白友好版
├── README.md                     ← 本文件
├── config.yaml                   ← VL模型地址（唯需修改的配置）
├── requirements.txt
└── scripts/
    ├── run_all.md                ← 总控 prompt（一句命令）
    ├── batch_extract.py          ← 阶段一：图像识别脚本
    ├── cluster.py                ← 阶段二：聚类脚本
    ├── phase2_auto_modules.md    ← 阶段二前置：自动分模块
    ├── phase3_gap_analysis.md    ← 阶段三：框架补全
    ├── phase4_lecture_notes.md   ← 阶段四：讲义生成
    └── phase5_marp_slides.md     ← 阶段五：幻灯片生成+渲染
```
