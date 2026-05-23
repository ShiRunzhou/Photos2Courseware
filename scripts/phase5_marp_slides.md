# 阶段五：Marp 幻灯片生成与渲染

## 任务目标

将阶段四的讲义 Markdown 文件逐模块转化为 Marp 格式幻灯片，并通过 Marp CLI 渲染为 PPTX。

## 输入文件

- `.workbuddy/lecture_notes/*.md`（阶段四产出）

## 输出文件

- `.workbuddy/marp_slides/{模块id}_{标签}.md`（Marp 源文件）
- `.workbuddy/marp_slides/output/{模块id}_{标签}.pptx`（渲染后的 PPTX）

## Marp 文件模板

每个 Marp MD 文件必须以以下 front matter 开头：

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

第一页为模块封面（`<!-- _class: lead -->`），最后一页为模块小结（`<!-- _class: lead -->`）。

## 分页规则（关键）

Marp 用 `---` 作为分页符。每页幻灯片需满足：

### 文字密度
- 每页投影文字 ≤ 150 字（不包括表格）
- 表格控制在 5 行以内（含表头）
- 一条 `|------|` 分隔线算 1 行

### 结构约束
- 同一页内**禁止**两个独立的 `##` 或 `###` 小节叠加
- 同一页内**禁止**两个独立的表格叠加
- 遇到叠加情况 → 拆分为独立页

### 表格拆分示例

```markdown
# ❌ 错误（11行表格，会溢出）
| 步骤 | 操作 | 参数 |
|------|------|:---:|
| ① | ... | ... |
| ...（共10行数据）...

# ✅ 正确（拆为两页）
## 操作流程（一）
| 步骤 | 操作 | 参数 |
|------|------|:---:|
| ① | ... | ... |
| ...（前5行）...

---

## 操作流程（二）
| 步骤 | 操作 | 参数 |
|------|------|:---:|
| ⑥ | ... | ... |
| ...（后5行）...
```

### 多板块叠加示例

```markdown
# ❌ 错误（两个独立表格）
## 设备分类
### 按使用场景
| 类型 | 特点 |
...
### 按加热模式  
| 特点 | 加热块 | 锅炉 |
...

# ✅ 正确（拆为独立页）
## 设备分类：按使用场景
| 类型 | 特点 |
...

---

## 设备分类：按加热模式
| 特点 | 加热块 | 锅炉 |
...
```

### 超长文本
- 连续 6+ 个列表项/段落 → 拆为两页
- 摘要页用小号文字或代码块样式

## 内容精简原则

从讲义到幻灯片的文字转换：

| 讲义 | 幻灯片 |
|------|--------|
| 完整段落 | 关键词 + 箭头/符号 |
| 举例：咖啡树适宜生长在南北回归线之间的区域 | 南北回归线之间的热带/亚热带 |
| 举例：绿原酸在烘焙后大幅降解，产生奎宁酸和咖啡酸 | 绿原酸→降解→奎宁酸+咖啡酸 |

- 保留核心数据和对比关系
- 删除过渡句、修饰语、重复表述
- 表格列数 ≥ 4 时考虑精简列或改用列表

## 配图标记

讲义中的 `[配图建议：xxx]` **不要**放入幻灯片 Markdown——幻灯片是纯文字排版，配图标记仅保留在讲义中供人工参考。

## 渲染命令

全部 Marp MD 生成完毕后，执行：

```bash
# Windows 需要设置 Chrome 路径
export CHROME_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe"

cd .workbuddy/marp_slides
for f in *.md; do
  marp "$f" --allow-local-files --pptx -o "output/$(basename "$f" .md).pptx"
done
```

> `--allow-local-files` 是必须的（即使当前无图片，未来可能插入）

## 产出交付

渲染完成后，复制最终产出到照片目录的 `output/`：

```bash
PHOTO_DIR="D:\照片目录"
mkdir -p "$PHOTO_DIR/output"
cp .workbuddy/lecture_notes/*.md "$PHOTO_DIR/output/"
cp .workbuddy/marp_slides/output/*.pptx "$PHOTO_DIR/output/"
```

## 常见问题

| 问题 | 原因 | 修复 |
|------|------|------|
| 内容溢出/截断 | 多板块堆叠或表格过长 | 拆分为独立页 |
| 底部留白不足 | 默认主题紧凑 | 已在 CSS 中解决（`padding-bottom: 48px`） |
| PPTX 文件被锁 | PowerPoint 中打开着 | 关闭预览后重渲染 |
| 渲染超时 | 页数过多 (>15页) | 单次渲染时间可能需 >30s，单独重试 |
