# stemcell

> 「重置 → 克隆 → 分化 → 质控」四阶段Agent流水线MVP。
> 把原始输入素材提炼为通用底座，批量派生出多视角候选方案，自动打分筛选。

灵感来自iPS干细胞分化范式：体细胞重编程为多能干细胞 → 克隆筛选 → 定向分化 → 质量控制。

## 核心流程

```
原始输入 → [Reset] 提炼结构化底座 → [Clone] 多视角副本派生
→ [Differentiate] 批量生成候选 → [Quality] 打分排序 → 输出Top-N
```

## 安装

```bash
pip install -e .
```

配置API密钥：

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 填入你的 API Key
```

## 使用

```bash
# 基本用法
stemcell run --input examples/sample_input.md

# 指定视角和候选数量
stemcell run --input input.md --perspectives conservative,engineering,risk --count 8

# 只输出Top 3
stemcell run --input input.md --top 3

# 导出为JSON
stemcell run --input input.md --format json --output result.json
```

## 四模块说明

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Reset | 清洗原始素材，提炼结构化底座 | 原始文本/文档 | JSON底座 |
| Clone | 基于底座派生多视角副本 | 底座 + 视角标签 | N份带视角的副本 |
| Differentiate | 每份副本独立生成候选方案 | 副本 + 环境信号 | N份候选输出 |
| Quality | 多维度打分排序 | 候选集合 | 排序后的Top-N |

## 项目结构

```
stemcell/
├── cli.py              # 命令行入口
├── pipeline.py         # 流水线编排
├── llm.py              # LLM调用封装
├── modules/
│   ├── reset.py        # 重置模块
│   ├── clone.py        # 克隆模块
│   ├── differentiate.py # 分化模块
│   └── quality.py      # 质控模块
└── prompts/            # 各模块提示词模板
```

## 设计原则

1. **参数化优先**：选视角、调数量，不写长prompt
2. **批量生成**：一次产出多个候选，不靠单次生成完美
3. **自动筛选**：打分排序，用户只看Top-N
4. **沙盒后置**：MVP不含沙盒仿真，P1迭代加入

## License

MIT
