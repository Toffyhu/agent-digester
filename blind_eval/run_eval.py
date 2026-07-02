"""30样本盲评准备脚本 + 类比库自动扩充

1. 30样本 (6领域×5篇) → v0.3 vs Baseline 对照
2. 输出格式化对照表供人工评分
3. 类比库自动扩充: 每次成功类比自动入库"""

import asyncio, os, sys, json, time, re, yaml, hashlib
from pathlib import Path

# ⚠️ 安全的API Key加载方式：从环境变量读取，不硬编码
_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not _DEEPSEEK_KEY or _DEEPSEEK_KEY.startswith("sk-") is False:
    print("⚠️ 请设置环境变量 DEEPSEEK_API_KEY 后再运行")
    print("   export DEEPSEEK_API_KEY='你的DeepSeek API Key'")
    sys.exit(1)

sys.path.insert(0, "/workspace")
from agent_digester import DigestionPipeline

# ═══════════════════════════════════════
# 30个测试样本 (6领域×5篇, 200-400字/篇)
# ═══════════════════════════════════════

SAMPLES = [
    # ── 哲学 (5篇) ──
    {"domain":"哲学","title":"康德的先验演绎","text":"康德在《纯粹理性批判》中提出，知性范畴是经验可能性的条件，而非经验的结果。这意味着我们不是被动地接收世界的印象，而是主动地用先天的概念框架来组织经验。空间和时间不是外部世界的属性，而是我们感知世界的方式。"},
    {"domain":"哲学","title":"海德格尔的此在","text":"此在(Dasein)是海德格尔用来指称人的存在的专门术语。此在的特殊之处在于，它不仅存在，而且能够对自己的存在有所领会。此在的本质在于它的生存——它不是现成的东西，而是一种可能性。此在总是已经在世界之中，与世界中的其他存在者打交道。"},
    {"domain":"哲学","title":"维特根斯坦语言游戏","text":"维特根斯坦后期哲学提出语言游戏的概念。语言的意义不在于指称对象，而在于使用。就像不同的游戏有不同的规则，不同的语言活动也有不同的规则。追问一个词的本质是什么是没有意义的——要看它在实际生活中的用法。"},
    {"domain":"哲学","title":"笛卡尔我思故我在","text":"笛卡尔试图找到一个不可怀疑的起点。他怀疑一切——感官、世界、甚至自己的身体。但当他怀疑时，他发现怀疑本身是不可怀疑的——因为即使在怀疑，思考行为本身证明了他存在。这就是我思故我在：只要我在思考，我就必须存在。"},
    {"domain":"哲学","title":"尼采的永恒轮回","text":"尼采提出永恒轮回的思想实验：如果有一个魔鬼告诉你，你的人生将无限次重复，每一秒都一模一样地重演——你会诅咒这个魔鬼，还是把这当作最大的肯定？这个思想不是字面意义上的宇宙论，而是对生命态度的终极检验。"},

    # ── 法律 (5篇) ──
    {"domain":"法律","title":"合同的要约与承诺","text":"合同成立需要两个基本要素：要约和承诺。要约是一方当事人向另一方提出的订立合同的意思表示，内容必须明确具体。承诺是受要约人同意要约的意思表示，必须与要约的内容一致。如果承诺对要约的内容作出实质性变更，则构成新的要约。"},
    {"domain":"法律","title":"善意取得制度","text":"善意取得是指无权处分人将动产转让给受让人，如果受让人在受让时是善意的（不知道也不应当知道转让人无权处分），则可以取得该动产的所有权。这个制度保护交易安全，在保护原所有权人和善意受让人之间选择了后者。"},
    {"domain":"法律","title":"诉讼时效","text":"诉讼时效是指权利人在法定期间内不行使权利，期间届满后义务人获得抗辩权的制度。普通诉讼时效为三年。时效制度的目的是督促权利人及时行使权利、维护社会秩序稳定、避免因时间久远导致证据灭失。"},
    {"domain":"法律","title":"正当防卫","text":"正当防卫是指为了使国家、公共利益、本人或者他人的人身、财产和其他权利免受正在进行的不法侵害，而采取的制止不法侵害的行为。正当防卫不负刑事责任。但防卫行为必须没有明显超过必要限度，否则构成防卫过当。"},
    {"domain":"法律","title":"无因管理","text":"无因管理是指没有法定或约定的义务，为避免他人利益受损失而管理他人事务的行为。管理人有权请求受益人偿还由此支出的必要费用。但管理行为必须符合受益人的真实意思，否则可能构成侵权。"},

    # ── 科学 (5篇) ──
    {"domain":"科学","title":"量子叠加态","text":"量子叠加态是量子力学的核心概念：一个量子系统在被测量之前，可以同时处于多个状态的叠加中。薛定谔的猫思想实验说明：在打开盒子之前，猫既死又活。测量行为本身会使叠加态坍缩到一个确定的状态。"},
    {"domain":"科学","title":"自然选择","text":"达尔文的自然选择理论指出，生物个体之间存在变异，某些变异使个体在生存和繁殖方面具有优势。这些优势个体更可能存活并传递其性状给后代。经过多代积累，有利性状在种群中变得越来越普遍，从而导致物种的演化。"},
    {"domain":"科学","title":"相对论的时间膨胀","text":"爱因斯坦的狭义相对论预言，运动中的时钟走得比静止的时钟慢。这个效应在接近光速时变得显著。例如，一个以0.9倍光速旅行的宇航员，他的时间流逝只有地球上的约44%。这不是时钟的机械故障，而是时间本身的性质。"},
    {"domain":"科学","title":"DNA复制","text":"DNA复制是半保留式的：双螺旋解开后，每条单链作为模板合成新的互补链。酶沿着DNA移动，读取碱基序列（A-T, C-G配对），逐个添加互补核苷酸。最终产生两个完全相同的DNA分子，每个包含一条原始链和一条新链。"},
    {"domain":"科学","title":"光合作用","text":"光合作用是植物利用光能将二氧化碳和水转化为葡萄糖和氧气的过程。叶绿体中的叶绿素吸收红光和蓝光，激发电子进入高能态。这些高能电子通过电子传递链驱动ATP和NADPH的合成，最终在卡尔文循环中固定二氧化碳。"},

    # ── 经济 (5篇) ──
    {"domain":"经济","title":"通货膨胀","text":"通货膨胀是指整体物价水平持续上涨的经济现象。当货币供应量超过经济实际产出时，过多的货币追逐有限的商品，导致货币购买力下降。温和通胀被视为经济健康的信号，但恶性通胀会严重破坏经济秩序。"},
    {"domain":"经济","title":"比较优势","text":"大卫·李嘉图提出比较优势理论：即使一个国家在所有产品的生产上都比另一个国家效率更低，两国仍然可以通过贸易获益。关键是每个国家专注于生产自己相对效率最高（机会成本最低）的产品，然后交换。"},
    {"domain":"经济","title":"道德风险","text":"道德风险指一方在受到某种形式的保护后，行为变得比没有保护时更加冒险。典型例子是：有保险的人可能比没有保险的人更不注意防范风险，因为他们知道损失会被补偿。这在金融监管中是一个核心考量。"},
    {"domain":"经济","title":"囚徒困境","text":"囚徒困境是博弈论的经典模型：两个嫌疑人被分开审讯，如果都沉默各判1年，都坦白各判5年，一人坦白一人沉默则坦白者释放沉默者判10年。从个人理性出发，坦白是占优策略，但双方都坦白的结果比都沉默更差。"},
    {"domain":"经济","title":"吉芬商品","text":"吉芬商品是经济学中的反常现象：当价格上涨时，需求反而增加。这是因为该商品在消费者预算中占比极大，价格上涨使实际收入下降，消费者被迫减少更贵的替代品消费，反而增加对该商品的需求。典型的例子是19世纪爱尔兰的土豆。"},

    # ── 技术 (5篇) ──
    {"domain":"技术","title":"MapReduce","text":"MapReduce是一种分布式计算模型。Map阶段将输入数据拆分为键值对，在多台机器上并行处理；Shuffle阶段将相同键的数据汇集到同一台机器；Reduce阶段对每个键的数据进行聚合计算。核心思想是分而治之，将大问题拆为小问题并行求解。"},
    {"domain":"技术","title":"TCP三次握手","text":"TCP协议通过三次握手建立可靠连接。客户端先发送SYN包请求连接；服务器回复SYN+ACK包确认收到；客户端再回复ACK包确认。这个过程确保双方都有收发能力，协商初始序列号，防止历史连接被错误建立。"},
    {"domain":"技术","title":"公钥加密","text":"公钥加密使用一对数学上相关的密钥：公钥可以公开分享用于加密，私钥必须保密用于解密。任何人都可以用你的公钥加密消息，但只有拥有私钥的你能解密。RSA算法的安全性基于大数因数分解的数学困难性。"},
    {"domain":"技术","title":"垃圾回收GC","text":"垃圾回收是自动内存管理机制。程序运行时不断分配内存，当某些内存不再被任何引用指向时，垃圾回收器识别并释放这些内存。常用算法包括标记-清除（遍历引用链标记存活对象后清除其余）和分代回收（新对象和老对象分开处理）。"},
    {"domain":"技术","title":"共识算法Paxos","text":"Paxos是分布式系统中达成共识的经典算法。多个节点通过提案-投票机制，即使部分节点故障或消息延迟，仍能对某个值达成一致。基本流程：提议者提出编号提案，接受者承诺不接收更小编号的提案，多数派接受后值被确定。"},

    # ── 心理 (5篇) ──
    {"domain":"心理","title":"确认偏误","text":"确认偏误是指人们倾向于寻找、解释和记忆那些支持自己已有信念的信息，同时忽略或贬低相反的证据。这不是故意的不诚实，而是大脑的一种无意识倾向。确认偏误在政治观点、投资决策甚至科学研究中都广泛存在。"},
    {"domain":"心理","title":"邓宁-克鲁格效应","text":"邓宁-克鲁格效应描述了一种认知偏差：能力较低的个体倾向于高估自己的能力，而能力较高的个体则倾向于低估自己。这是因为缺乏能力的人同时也缺乏识别自己缺乏能力的元认知能力。随着知识的增长，人们往往会认识到自己不知道的更多。"},
    {"domain":"心理","title":"斯坦福监狱实验","text":"1971年津巴多的斯坦福监狱实验将志愿者随机分配为囚犯和狱警。原本计划两周的实验在第六天就被迫终止，因为参与者迅速内化了角色——狱警变得残忍，囚犯变得顺从压抑。这揭示了情境力量对行为的巨大影响，远超过个体性格。"},
    {"domain":"心理","title":"峰终定律","text":"峰终定律指出，人们对一段经历的评判主要取决于两个时刻：体验的高峰（最好或最坏的瞬间）和结束时的感受，而非经历的平均质量。这意味着一个过程糟糕但结局美好的经历，在记忆中的评价会高于一个平稳但平庸的经历。"},
    {"domain":"心理","title":"基本归因错误","text":"基本归因错误是指人们在解释他人行为时，过度强调内在性格因素，而低估外部情境因素。当看到别人迟到时，我们倾向于认为这人懒散（内在归因），而不是考虑可能堵车了（情境归因）。但在解释自己的行为时，我们往往反过来。"},
]

# ═══════════════════════════════════════
# 配置
# ═══════════════════════════════════════

CONFIG = {
    "providers": {
        "deepseek": {"base_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY",
            "models": {"v4": {"id": "deepseek-chat", "context_window": 65536,
                     "cost_per_1k_input": 0.00058, "cost_per_1k_output": 0.00348}}}
    },
    "agent_model_mapping": {
        "s1_simplify": {"primary": "deepseek/v4"},
        "s2_analogy": {"primary": "deepseek/v4"},
        "s3_hook": {"primary": "deepseek/v4"},
    }
}
with open("/tmp/eval_config.yaml", "w") as f:
    yaml.dump(CONFIG, f)

# ═══════════════════════════════════════
# Baseline: 单次 Prompt (对照)
# ═══════════════════════════════════════

BASELINE_PROMPT = """请将以下文本转化为通俗易懂的解释。

要求:
1. 先给一个具象类比
2. 用一句话总结核心概念
3. 列出3个要点
4. 最后提一个引人思考的问题

输出JSON: {"analogy":"","essence":"","points":["","",""],"question":""}。只输出JSON。"""

from openai import OpenAI
baseline_client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")

def run_baseline(text: str) -> dict:
    r = baseline_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"system","content":BASELINE_PROMPT},{"role":"user","content":text[:3000]}],
        temperature=0.4, max_tokens=1024,
    )
    try:
        raw = r.choices[0].message.content.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {"error": raw[:200]}
    except:
        return {"error": raw[:200]}


# ═══════════════════════════════════════
# 类比库自动扩充
# ═══════════════════════════════════════

from agent_digester.assets.analogy_bank.patterns import PATTERNS, AnalogyPattern

def auto_expand_bank(domain: str, concept: str, analogy: dict, score: int = 3):
    """将新类比存入类比库"""
    # 检查是否已存在高度相似的类比
    scene = analogy.get("analogy_scene", "")[:60]
    for p in PATTERNS:
        for vc in p.verified_cases:
            if vc.get("analogy", "")[:40] == scene[:40]:
                return  # 已存在，跳过

    # 找最匹配的模式
    best = None
    for p in PATTERNS:
        if domain.lower() in [d.lower() for d in p.candidate_domains] or \
           domain.lower() in p.pattern_type.lower():
            best = p
            break

    if best and best.verified_cases:
        best.verified_cases.append({
            "concept": concept[:80],
            "analogy": analogy.get("analogy_scene", "")[:120],
            "score": score,
        })
        print(f"    📚 类比库扩充: {best.pattern_id} ← {concept[:30]}")


# ═══════════════════════════════════════
# 主流程
# ═══════════════════════════════════════

async def main():
    all_results = []
    total_start = time.time()
    total_cost = 0.0
    
    results_dir = Path("/workspace/blind_eval")
    results_dir.mkdir(exist_ok=True)

    for idx, sample in enumerate(SAMPLES):
        dom = sample["domain"]
        title = sample["title"]
        text = sample["text"]
        
        print(f"[{idx+1:02d}/30] {dom}: {title}...", end=" ", flush=True)
        
        # ── v0.3 消化 ──
        pipeline = DigestionPipeline(config_path="/tmp/eval_config.yaml", domain="日常经验")
        result_v3 = await pipeline.digest(text=text, title=title, source_type=dom)
        total_cost += result_v3.total_cost_usd
        o3 = result_v3.final_output
        
        # ── Baseline 单次Prompt ──
        baseline = run_baseline(text)
        
        # 自动扩充类比库
        if o3 and o3.core_analogy and len(o3.core_analogy) > 20:
            auto_expand_bank(dom, title, {"analogy_scene": o3.core_analogy}, score=3)
        
        # 构建对照条目
        entry = {
            "id": f"{idx+1:02d}",
            "domain": dom,
            "title": title,
            "text": text[:100] + "...",
            "v3": {
                "time": f"{result_v3.total_duration_seconds:.1f}s",
                "cost": f"${result_v3.total_cost_usd:.4f}",
                "analogy": o3.core_analogy if o3 else "",
                "essence": o3.one_line_essence if o3 else "",
                "why": o3.why_you_care if o3 else "",
                "points": [{"title": p.title, "content": p.content} for p in (o3.skeleton_points if o3 else [])],
                "hook": o3.micro_action if o3 else "",
            },
            "baseline": {
                "analogy": baseline.get("analogy", ""),
                "essence": baseline.get("essence", ""),
                "points": [p for p in baseline.get("points", []) if p],
                "question": baseline.get("question", ""),
            },
            "ratings": {
                "v3_understand": "", "v3_analogy": "", "v3_natural": "",
                "bl_understand": "", "bl_analogy": "", "bl_natural": "",
                "winner": "", "notes": "",
            }
        }
        all_results.append(entry)
        print(f"✅ v3={entry['v3']['time']} | baseline=OK")

    total_time = time.time() - total_start

    # ── 输出对照表 Markdown ──
    md = f"""# 30样本盲评对照表

**生成时间**: {time.strftime('%Y-%m-%d %H:%M')}
**测试方案**: v0.3 (3Agent+规则层+类比库) vs Baseline (单次Prompt)
**总耗时**: {total_time:.0f}s | **总成本**: ${total_cost:.4f}
**平均**: {total_time/30:.1f}s/篇 | ${total_cost/30:.4f}/篇

---

## 评分说明

请逐行对比两列输出，对以下维度打分 (1-5):

| 维度 | 说明 |
|------|------|
| **可理解性** | 读完能否用自己的话复述核心概念 |
| **类比质量** | 类比是否精准抓住结构本质 |
| **自然度** | 读起来是否像人写的，有无AI感 |

在最后一列标注 **胜出方** (A=v0.3 / B=Baseline / =持平)

---

## 对照表 (盲评: A和B随机排列，不要看表头)

"""
    
    import random
    rng = random.Random(42)
    for entry in all_results:
        # 随机决定A/B对应v3/baseline
        if rng.random() > 0.5:
            a, b = entry["v3"], entry["baseline"]
            a_label, b_label = "v3", "baseline"
        else:
            a, b = entry["baseline"], entry["v3"]
            a_label, b_label = "baseline", "v3"
        
        md += f"### {entry['id']}. [{entry['domain']}] {entry['title']}\n\n"
        md += f"> 原文: {entry['text']}\n\n"
        
        md += "| 维度 | 方案A | 方案B | A评分 | B评分 | 胜出 |\n"
        md += "|------|-------|-------|-------|-------|------|\n"
        
        md += f"| 类比 | {a['analogy'][:60]}... | {b['analogy'][:60]}... | | | |\n"
        md += f"| 本质 | {a['essence'][:60]}... | {b['essence'][:60]}... | | | |\n"
        a_p1 = (a['points'][0].get('title','') if isinstance(a['points'][0], dict) else str(a['points'][0])) if a.get('points') else ''
        b_p1 = (b['points'][0].get('title','') if isinstance(b.get('points',[]), list) and b['points'] and isinstance(b['points'][0], dict) else str(b['points'][0]) if b.get('points') and len(b['points'])>0 else '')
        md += f"| 要点1 | {a_p1[:50]} | {b_p1[:50]} | | | |\n"
        md += f"| 钩子 | {a.get('hook','')[:60]}... | {b.get('question','')[:60]}... | | | |\n"
        
        md += f"\n**综合**: A={a_label} | B={b_label} | 胜出: ___ | 备注: ___\n\n"
        md += "---\n\n"

    with open(results_dir / "comparison_table.md", "w") as f:
        f.write(md)

    # ── 保存完整JSON数据 ──
    with open(results_dir / "raw_data.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # ── 统计摘要 ──
    print(f"\n{'='*60}")
    print(f"  30样本盲评准备完成")
    print(f"{'='*60}")
    print(f"  总耗时: {total_time:.0f}s ({total_time/30:.1f}s/篇)")
    print(f"  总成本: ${total_cost:.4f}")
    print(f"  输出文件:")
    print(f"    📄 {results_dir}/comparison_table.md  (盲评对照表)")
    print(f"    📄 {results_dir}/raw_data.json        (原始数据)")
    print(f"  类比库扩充: {sum(1 for p in PATTERNS for v in p.verified_cases)} 条已验证案例")


asyncio.run(main())
