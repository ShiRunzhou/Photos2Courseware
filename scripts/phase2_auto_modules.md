# 阶段二前置：自动识别知识模块

## 任务目标

读取阶段一的提取结果，自动识别培训包含哪些知识模块，并生成 `config.yaml` 中的 `modules` 配置。

## 输入文件

- `.workbuddy/extracted/IMG_*.json`（阶段一产出，全部照片的提取结果）

## 输出

在 `config.yaml` 中自动填充 `modules` 部分。

## 执行方式

对 AI agent 说：「读取 .workbuddy/extracted/ 中的提取结果，自动识别培训主题的知识模块，写入 config.yaml 的 modules 部分。」

## AI agent 执行逻辑

1. 读取所有 `extracted/IMG_*.json`
2. 汇总全部提取文本
3. 分析内容中的**高频主题词**和**知识点聚类**
4. 将内容归纳为 3-8 个知识模块
5. 为每个模块生成 `id`（A-Z）、`label`（模块名）、`keywords`（3-5 个关键词）
6. 写入 `config.yaml` 覆盖原来的 `modules` 示例

## 示例输出

```yaml
modules:
  - id: A
    label: "灭火器材与使用"
    keywords: ["灭火器", "消防栓", "干粉", "二氧化碳", "喷射"]
  - id: B
    label: "火灾逃生知识"
    keywords: ["疏散", "安全出口", "浓烟", "匍匐", "湿毛巾"]
  - id: C
    label: "消防法规制度"
    keywords: ["消防法", "责任", "处罚", "备案", "检查"]
```

## 注意

- 模块数量不宜过多（建议 3-8 个）
- 每个模块的关键词应从提取文本中实际出现的词中选取
- 如果照片覆盖的内容极少（< 3 张），可用一个"其他/补充"模块收尾
