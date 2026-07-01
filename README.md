# agent-digester — 认知消化工具 🧠

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于认知科学的六层内容转换引擎。将任意输入（文章/论文/主题）消化为符合人类认知习惯的结构化输出。

## 设计原理

```
输入 → [翻译前置(可选)] → 难度评估 → 锚点识别 → 六层重构 → 叙事优化 → 认知缺口 → 输出
```

### 六层输出结构

| Layer | 说明 | 认知依据 |
|-------|------|----------|
| 0 核心类比 | 一句话具象画面 | 锚定效应 + 双编码 |
| 1 一句话本质 | ≤50字核心 | 工作记忆瓶颈 |
| 2 跟你有关 | 建立动机 | 认知负荷筛选 |
| 3 具象→抽象 | 从场景到概念 | 建构主义 |
| 4 核心骨架 | 3-5要点+视觉 | 4±1组块 |
| 5 微行动 | 触发主动思考 | 生成效应 |

### 七条认知铁律

Miller's Law / 认知负荷 / 锚定前置 / 叙事编码 / 生成效应 / 双编码 / 间隔强化

## 安装

```bash
pip install agent-digester

# 如需翻译前置功能
pip install agent-digester[translator]
```

## 快速开始

```python
from agent_digester import DigestionPipeline, UserProfile

pipeline = DigestionPipeline()
result = await pipeline.digest(
    text="需要消化的文本...",
    title="文章标题",
    profile=UserProfile(user_id="user_001"),
)

# 输出为 Markdown
print(result.final_output.to_markdown())

# 输出为公众号格式
print(result.final_output.to_wechat())
```

## 依赖

- [agent-core](https://github.com/Toffyhu/agent-core) — 多Agent通用底座
- [multi-agent-translator](https://github.com/Toffyhu/multi-agent-translator) (可选) — 外文翻译前置

## 许可证

MIT
