"""三阶验证引擎 — 知识内化验证

基于学习科学中的生成效应和检索练习原理:
- Stage 1: 自检题  — 2-3道题目检测理解程度
- Stage 2: 实践任务 — 1个可执行的具体练习
- Stage 3: 间隔提醒 — 按遗忘曲线排期复习
"""

import json, re
from agent_core import ModelRegistry
from agent_digester.pipeline.orchestrator import _Agent

PROMPT_VERIFY = """基于消化的内容，设计三阶验证。

Stage 1 — 自检题 (2-3题):
- 至少1道选择题 + 1道简答题
- 不能直接问定义，要问「如果...会怎样」「这两个概念有什么区别」「用你自己的话说」
- 每道题标注: 难度(易/中/难)、对应的核心概念

Stage 2 — 实践任务 (1个):
- 具体、可执行、5-15分钟能完成
- 不是一个笼统建议，而是明确的任务
- 标注完成标准: 「当你能够...时，说明你掌握了」

Stage 3 — 间隔提醒 (1条):
- 给出一句话回顾提示（不显示答案，让用户自己想）
- 标注首次间隔: 1天后

输出JSON:
{
  "stage1_selfcheck": [
    {"question":"题目","answer":"参考答案","difficulty":"易|中|难","target_concept":"对应概念","type":"choice|short_answer"}
  ],
  "stage2_practice": {"task":"具体任务","completion_criterion":"完成标准","estimated_time":"预计时间"},
  "stage3_reminder": {"cue":"一句话回顾提示","first_interval":"1天"}
}
只输出JSON。"""


class VerificationEngine:
    """三阶验证引擎"""
    
    def __init__(self, config_path="config/models.yaml"):
        self.registry = ModelRegistry(config_path)
    
    def generate(self, article: str, original_text: str = ""):
        """为消化文章生成三阶验证"""
        material = f"消化后文章:\n{article[:3000]}"
        if original_text:
            material += f"\n\n原文:\n{original_text[:1000]}"
        
        agent = _Agent(self.registry, "vfy_engine", PROMPT_VERIFY)
        resp, cost = agent.execute(material, temperature=0.3, max_tokens=2048)
        try:
            data = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group(0))
        except:
            data = {"stage1_selfcheck": [], "stage2_practice": {"task":""}, "stage3_reminder": {"cue":""}}
        
        return {
            "verification": data,
            "cost": f"${cost:.4f}",
        }
    
    def render(self, data: dict) -> str:
        """渲染三阶验证为可读格式"""
        v = data.get("verification", {})
        lines = ["\n---\n## 📝 检验一下\n"]
        
        # Stage 1
        sc = v.get("stage1_selfcheck", [])
        if sc:
            lines.append("### 自检题")
            for i, q in enumerate(sc, 1):
                diff = q.get("difficulty", "")
                lines.append(f"\n**{i}. {q.get('question', '')}**")
                lines.append(f"   *参考答案: {q.get('answer', '')}*")
            lines.append("")
        
        # Stage 2
        p = v.get("stage2_practice", {})
        if p.get("task"):
            lines.append("### 试试看")
            lines.append(f"{p.get('task', '')}")
            if p.get("completion_criterion"):
                lines.append(f"*完成标准: {p['completion_criterion']}*")
            if p.get("estimated_time"):
                lines.append(f"*预计: {p['estimated_time']}*")
            lines.append("")
        
        # Stage 3
        r = v.get("stage3_reminder", {})
        if r.get("cue"):
            lines.append("### 记得回来")
            lines.append(f"{r.get('cue', '')}")
            lines.append(f"*{r.get('first_interval', '1天后')}*")
        
        return "\n".join(lines)
