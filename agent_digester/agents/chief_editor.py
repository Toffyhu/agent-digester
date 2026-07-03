"""首席编审Agent v1.0 — 消化素材 → 自然文章

用户反馈解决的问题:
- 消除模板化标记（"别搞混了""换个角度想"...）
- 概念先定义后类比
- 整体编织而非碎片拼接
- 两个深度层次: popular(普及) / learning(学习)
"""

import json, re, time
from agent_core import ModelRegistry
from agent_digester.pipeline.orchestrator import _Agent

PROMPT_EDITOR_POPULAR = """你是科普主编。根据用户提供的素材，写成让零基础读者能读懂的文章。

规则:
1. 开门见山——第一段用直观类比抓人
2. 概念先定义后类比——说清XX是什么，再打比方
3. 一个核心类比贯穿全文，不重复引入新比喻
4. 像聊天而非教科书，300-500字
5. 禁止词汇: 首先/其次/最后/值得注意的是/综上所述/换个角度想/理解它的前提是/别搞混了/打个比方/你可能以为/其实不是/真正的意思是

直接写文章，不用标题分段，不用列表。"""

PROMPT_EDITOR_LEARNING = """你是深度主编。根据用户提供的素材，写成逻辑完整的解释文章。

读者: 有求知欲，愿花10分钟仔细理解。不需学术深度，但逻辑必须自洽。

规则:
1. 总-分-总: 一句话定义→逐层展开→收束回核心
2. 概念先定义后类比——定义清楚之前不上比喻
3. 🔑 单一类比递进: 全文只用一个核心类比体系。第一个子概念引入类比，后续子概念不要新开类比——延续同一个类比，展示其边界（哪适用、哪不适用）、或推向更深层
   - 例: 如果开篇用「双胞胎」类比纠缠态，讲非局域性时继续用这对双胞胎，但揭示「这种同步不能用来传消息」
   - 禁止: 每个子概念各配一个全新的比喻（读者会觉得重复累赘）
4. 有过渡句——日常场景自然引到抽象概念，不生硬拼接
5. 解释链完整——每个概念说明前提和结果
6. 钩子自然——从论证中生长出的追问，非突然插入
7. 长短句交替，段落间有呼吸感
8. 禁止词汇: 别搞混了/换个角度想/理解它的前提是/首先其次最后/打个比方/你可能以为

直接写文章，可用小标题。"""


def collect_material(topic, overview, digested):
    parts = [f"话题: {topic}", f"概述: {overview}", ""]
    for d in digested:
        name, data, cm = d["name"], d["data"], d.get("concept_map", [])
        parts.append(f"### {name}")
        essence = data.get("layer1_essence", "")
        if essence: parts.append(f"核心: {essence}")
        analogy = data.get("layer0_analogy", "")
        if analogy: parts.append(f"类比: {analogy}")
        if cm:
            baihua = cm[0].get("白话", "")
            if baihua: parts.append(f"定义: {baihua}")
            mc, corr = cm[0].get("misconception",""), cm[0].get("correction","")
            if mc and corr: parts.append(f"误解:{mc} 正解:{corr}")
            cf = cm[0].get("counterfactual","")
            if cf: parts.append(f"反事实:{cf}")
            pr = cm[0].get("prerequisite","")
            if pr: parts.append(f"前置:{pr}")
        pts = data.get("layer4_skeleton",[])
        if pts:
            parts.append("要点:")
            for p in pts:
                if p.get("title") and p.get("content"):
                    parts.append(f"  {p['title']}:{p['content']}")
        why = data.get("layer2_why","")
        if why: parts.append(f"关联:{why}")
        parts.append("")
    return "\n".join(parts)


def render_knowledge_map(knowledge_map: dict) -> str:
    """渲染延伸阅读三角卡片"""
    if not knowledge_map:
        return ""
    
    lines = ["\n---\n## 📖 接下来该读什么\n"]
    
    prereq = knowledge_map.get("prerequisites", [])
    if prereq:
        lines.append("**前置概念**（建议先补）:")
        for p in prereq:
            lines.append(f"- {p}")
        lines.append("")
    
    extensions = knowledge_map.get("extensions", [])
    if extensions:
        lines.append("**延伸概念**（深入方向）:")
        for e in extensions:
            lines.append(f"- {e}")
        lines.append("")
    
    apps = knowledge_map.get("applications", [])
    if apps:
        lines.append("**实际应用**（懂了能干嘛）:")
        for a in apps:
            lines.append(f"- {a}")
        lines.append("")
    
    return "\n".join(lines)


class ChiefEditor:
    def __init__(self, config_path="config/models.yaml"):
        self.registry = ModelRegistry(config_path)
    
    def edit(self, topic, overview, digested, depth="learning", knowledge_map=None):
        material = collect_material(topic, overview, digested)
        prompt = PROMPT_EDITOR_POPULAR if depth == "popular" else PROMPT_EDITOR_LEARNING
        agent = _Agent(self.registry, f"ed_{depth}", prompt)
        st = time.time()
        resp, cost = agent.execute(
            f"请根据以下素材写文章:\n\n{material}",
            temperature=0.5, max_tokens=2048 if depth == "popular" else 3072,
        )
        return {
            "article": resp.strip(),
            "depth": depth,
            "time": f"{time.time()-st:.1f}s",
            "cost": f"${cost:.4f}",
            "knowledge_map": render_knowledge_map(knowledge_map or {}),
        }
