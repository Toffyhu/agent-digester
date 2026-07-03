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

PROMPT_EDITOR_POPULAR = """你是科普主编。根据素材写一篇让普通人能读懂的文章。

不要照搬素材中的术语解释。你是一个解释者——把素材当作参考资料，重新用自己的话讲出来。

参考下面两段解释的风格（不是内容，是风格）:

风格参考A（好解释）:
「你有没有想过，为什么房间不收拾就会越来越乱？这不是你懒，是宇宙规律。物理学家管它叫熵增——任何封闭系统，混乱度只会增加不会减少。就像沙滩上的沙堡，潮水总会抹平它。这就是为什么你需要不断整理、不断投入能量。」

特点: 从日常场景切入 → 一句话点破概念 → 类比强化 → 收尾关联到读者体验

风格参考B（好解释）:
「假设你现在去银行存100块，年利率10%。第一年变110，第二年变121——不是120。多出来的1块，是利息的利息。这就是复利。它不性感，但它是宇宙中最强大的力量之一。爱因斯坦说复利是世界第八大奇迹——不是因为它复杂，而是因为大多数人不理解它在时间尺度上的威力。」

特点: 用读者的第一人称体验 → 数字具体化 → 反转常识 → 名人佐证但不啰嗦

你的文章: 300-500字，自然段落，不要标题。"""

PROMPT_EDITOR_LEARNING = """你是深度主编。根据素材写成一篇逻辑完整的解释。

把素材当作参考资料——重新组织、重新表达，用自己的话讲。你不是在填表，是在写一篇文章。

结构指引（不是模板，是思路）:
- 开篇就让人意外: 先给一个反直觉的事实或问题，不要"XX是量子力学的核心概念"
- 概念先定义后类比: 说清楚是什么，再给类比
- 一个核心类比贯穿全文: 用同一个比喻体系层层深入，不每个概念换一个新比喻
- 每个关键概念至少有一个「你可以这样理解它」的日常入口
- 结尾从论证自然生长出一个问题，不是硬加上去的

好文章的特点:
- 段落长短交替（长段深入→短句点醒→中段过渡）
- 像在跟一个聪明但不懂这个领域的朋友解释
- 能让人读完放下手机想了三秒钟

直接写文章。可用小标题。"""

def post_clean(text: str) -> str:
    """后处理清洗: 移除残留的模板化表述"""
    replacements = {
        "真正的意思是": "",
        "你可能以为": "有些人以为",
        "你可能觉得": "有人会觉得",
        "其实不是。": "但事实更微妙：",
        "别搞混了：": "",
        "换个角度想：": "",
        "理解它的前提是": "这需要先理解",
        "打个比方：": "",
        "首先，": "",
        "其次，": "",
        "最后，": "",
        "值得注意的是，": "",
        "综上所述，": "",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    # 清理多余空格和标点
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'。{2,}', '。', result)
    return result.strip()

def readability_score(text: str) -> dict:
    """可读性评估"""
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences:
        return {"level": "unknown", "avg_len": 0, "grade": "?"}
    
    avg_len = sum(len(s) for s in sentences) / len(sentences)
    
    # 简单映射: 中文句长→可读性
    if avg_len < 20:
        level, grade = "easy", "初中"
    elif avg_len < 35:
        level, grade = "medium", "高中"
    elif avg_len < 55:
        level, grade = "hard", "大学"
    else:
        level, grade = "very_hard", "研究生+"
    
    # 术语密度
    jargon = sum(1 for s in sentences for w in ['是','即','指','所谓','定义','因此','故而','换言之','必须','应当','从而','基于'] if w in s)
    jargon_density = jargon / max(len(sentences), 1)
    
    return {
        "level": level,
        "grade": grade,
        "avg_sentence_len": round(avg_len, 1),
        "jargon_density": round(jargon_density, 2),
        "sentences": len(sentences),
    }


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
        # 后处理: 清洗模板残留 + 可读性评估
        cleaned = post_clean(resp.strip())
        score = readability_score(cleaned)
        return {
            "article": cleaned,
            "depth": depth,
            "time": f"{time.time()-st:.1f}s",
            "cost": f"${cost:.4f}",
            "knowledge_map": render_knowledge_map(knowledge_map or {}),
            "readability": score,
        }
