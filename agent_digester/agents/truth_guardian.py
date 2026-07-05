"""求真校验Agent — 保真度核查 + 多源交叉验证

核心职责: 
  不是创作，是核查。在消化完成后、发布前，验证输出是否忠实地传达了原意。

三阶段核查:
  Phase A: 自检 — 逐条比对消化输出与原文的核心主张
  Phase B: 溯源 — 标记哪些解释来自原文、哪些是LLM的补充推断
  Phase C: 置信度 — 对每个推断性内容给出置信度评级
"""

import json, re, time
from agent_core import ModelRegistry
from agent_digester.pipeline.orchestrator import _Agent

# ── Phase A: 核心主张保真度核查 ──
PROMPT_FIDELITY = """你是学术校对。你的任务是逐条比对「消化后的解释」和「原文」，检查是否存在歪曲。

规则:
1. 从解释中提取3-5条核心主张（解释中明确陈述的结论性观点）
2. 逐条到原文中找对应的证据
3. 判断每条主张的保真度: 
   - 忠实: 原文明确支持这个观点
   - 扩展: 原文隐含了这个意思，解释做了合理延伸
   - 偏差: 解释添加了原文没有的观点
   - 错误: 解释与原文矛盾

输出JSON:
{
  "claims": [
    {
      "claim": "解释中的核心主张",
      "source_text": "原文中对应的段落或句子",
      "fidelity": "忠实|扩展|偏差|错误",
      "explanation": "判断依据"
    }
  ],
  "overall_score": "pass|review|fail",
  "critical_issues": ["需要修正的严重问题"]
}

只输出JSON。"""

# ── Phase B: 来源溯源 ──
PROMPT_SOURCE_TRACE = """你是溯源专家。分析一篇AI生成的解释文章，标记每个关键信息的来源。

规则:
1. 对解释中的每个核心观点，判断它来自哪里:
   - 原文: 直接从原文提取的
   - LLM推断: AI基于上下文自行补充的（如类比、日常例子、背景说明）
   - 外部知识: AI从自己的训练数据中引入的（如历史背景、相关理论）

2. 用简短标签标注每个推断或外部知识的可靠性（高/中/低）

输出JSON:
{
  "traced_items": [
    {
      "content": "解释中的一句话或一个观点",
      "source": "原文|LLM推断|外部知识",
      "reliability": "高|中|低",
      "note": "简短说明"
    }
  ],
  "inference_ratio": "推断内容占比（如: 40%）",
  "risk_items": ["需要读者注意的高风险推断"]
}

只输出JSON。"""

# ── Phase C: 置信度标记 — 事后标记而非修改原文 ──
def annotate_confidence(article: str, trace_result: dict) -> str:
    """在文章末尾附上溯源说明，不修改原文"""
    lines = ["\n---\n## 🔍 阅读说明\n"]
    
    risk_items = trace_result.get("risk_items", [])
    if risk_items:
        lines.append("以下内容为AI基于上下文推断，请以原文为准：")
        for item in risk_items:
            lines.append(f"- ⚠️ {item}")
        lines.append("")
    
    inference_ratio = trace_result.get("inference_ratio", "未知")
    lines.append(f"本文推断内容占比约 {inference_ratio}。")
    lines.append("标记「原文」的内容直接取自源文本；标记「推断」或「外部知识」的内容为AI补充，仅供参考。")
    
    return article + "\n".join(lines)


class TruthGuardian:
    """求真校验 — 在发布前验证消化输出的准确性"""
    
    def __init__(self, config_path="config/models.yaml"):
        self.registry = ModelRegistry(config_path)
    
    def verify(self, original_text: str, digested_article: str):
        """完整校验流程"""
        results = {}
        
        # Phase A: 保真度核查
        agent_a = _Agent(self.registry, "tg_fidelity", PROMPT_FIDELITY)
        resp_a, cost_a = agent_a.execute(
            f"原文:\n{original_text[:3000]}\n\n消化后:\n{digested_article[:3000]}",
            temperature=0.1, max_tokens=2048,
        )
        try:
            fidelity = json.loads(re.search(r'\{.*\}', resp_a, re.DOTALL).group(0))
        except:
            fidelity = {"overall_score": "review", "critical_issues": ["解析失败"]}
        
        # Phase B: 来源溯源
        agent_b = _Agent(self.registry, "tg_source", PROMPT_SOURCE_TRACE)
        resp_b, cost_b = agent_b.execute(
            f"原文:\n{original_text[:2000]}\n\n解释:\n{digested_article[:2000]}",
            temperature=0.1, max_tokens=2048,
        )
        try:
            trace = json.loads(re.search(r'\{.*\}', resp_b, re.DOTALL).group(0))
        except:
            trace = {"risk_items": [], "inference_ratio": "未知"}
        
        # Phase C: 置信度标记
        annotated = annotate_confidence(digested_article, trace)
        
        return {
            "fidelity": fidelity,
            "trace": trace,
            "annotated_article": annotated,
            "pass": fidelity.get("overall_score") == "pass",
            "cost": f"${cost_a + cost_b:.4f}",
        }
