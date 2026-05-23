# 一键执行：照片 → 培训课件

## 任务目标

给定一个照片文件夹和一个项目文件夹（Photos2Courseware），自动完成从照片到讲义和PPTX的全流程。

## 前置条件

- Python 3 已安装，依赖已安装（`pip install -r requirements.txt`）
- Node.js + Marp CLI 已安装（`npm install -g @marp-team/marp-cli`）
- 当前设备有可用的 AI 视觉模型（本地或云端，见 config.yaml）

## 执行方式

对任意 AI agent（WorkBuddy / Codex / Cursor / Claude Code 等）说：

> 请读取 Photos2Courseware/scripts/run_all.md 并执行其中的任务。
> 照片目录：`D:\你的照片文件夹`

## AI agent 自动执行步骤

按顺序完成以下全部步骤，每步完成后报告进度：

### 步骤 1：图像识别（脚本）
```bash
python Photos2Courseware/scripts/batch_extract.py \
  --dir "D:\照片目录" \
  --mode single
```
输出：`.workbuddy/extracted/IMG_*.json`

### 步骤 2：自动识别知识模块（AI 推理）
- 读取 `.workbuddy/extracted/` 中的所有 JSON
- 汇总全部提取文本
- 分析内容中的高频主题词和知识点聚类
- 将内容归纳为 3-8 个知识模块
- 每个模块生成 `id`（A-Z）、`label`（模块名）、`keywords`（3-5 个关键词）
- 写入 `config.yaml` 覆盖 `modules` 部分

### 步骤 3：主题聚类（脚本）
```bash
python Photos2Courseware/scripts/cluster.py --dir "D:\照片目录"
```
输出：`.workbuddy/cluster_result.json`

### 步骤 4：框架完整性分析与补全（AI 推理）
- 读取 `cluster_result.json`
- 对每个模块，对比完整领域知识体系，识别缺失但高度相关的内容
- 缺失类型包括：前置知识、实操配套、设备认知、行业体系、现代进展、对比补充
- 输出补全清单（记录在后续讲义生成时使用）

### 步骤 5：讲义生成（AI 推理）
- 逐模块读取聚类内容 + 补全清单
- 生成结构化 Markdown 讲义
- 格式要求：
  - 每个知识点用 `##` 标题
  - 关键数据用表格
  - 术语标注中英文
  - 框架补全内容用 `🆕 补充` 前缀
  - 适合配图的位置加 `[配图建议：xxx]`
- 保存到 `.workbuddy/lecture_notes/{模块id}_{标签}.md`

### 步骤 6：Marp 幻灯片生成（AI 推理）
- 逐模块读取讲义 Markdown
- 转化为 Marp 格式，要求：
  - 第一页为模块封面，最后一页为小结
  - 每页 ≤ 150 字投影文字
  - 表格控制在 5 行以内
  - 同一页禁止两个独立表格或两个 `##`/`###` 叠加
  - 遇到叠加 → 拆为独立页
- Marp 文件模板：
  ```yaml
  ---
  marp: true
  theme: default
  paginate: true
  size: 16:9
  style: |
    section { padding-bottom: 48px; }
  ---
  ```
- 保存到 `.workbuddy/marp_slides/{模块id}_{标签}.md`

### 步骤 7：渲染 PPTX（命令）
```bash
export CHROME_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe"
cd .workbuddy/marp_slides
for f in *.md; do
  marp "$f" --allow-local-files --pptx -o "output/$(basename "$f" .md).pptx"
done
```

### 步骤 8：产出交付
```bash
mkdir -p "D:\照片目录\output"
cp .workbuddy/lecture_notes/*.md "D:\照片目录\output\"
cp .workbuddy/marp_slides/output/*.pptx "D:\照片目录\output\"
```

## 最终产出

```
照片目录/output/
├── A_模块名.md
├── B_模块名.md
├── A_模块名.pptx
├── B_模块名.pptx
└── ...
```

## 错误处理

| 问题 | 处理 |
|------|------|
| 图像识别超时 | 重试单张，或增加 config.yaml 中的 timeout |
| 聚类结果模块数不合理 | 回到步骤 2 重新归纳模块 |
| 幻灯片内容溢出 | 回到步骤 6 拆分溢出页面 |
| PPTX 文件被锁 | 关闭 PowerPoint 预览后重渲染 |
