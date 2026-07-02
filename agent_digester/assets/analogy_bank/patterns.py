"""类比库 v0.1 — 20条认知结构模式

基于认知科学中常见的抽象结构类型，每条记录:
- 结构类型: 该概念的抽象认知结构
- 候选类比域: 适合用来类比该结构的日常/专业领域
- 已验证案例: 在消化测试中表现优秀的类比记录
- 避坑提示: 这个结构类比容易犯的错误

设计原则：存结构，不存文字。LLM 根据结构模式自行生成类比。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnalogyPattern:
    """类比结构模式"""
    pattern_id: str
    pattern_type: str          # 结构类型: causal / hierarchical / process / tradeoff / etc.
    description: str           # 模式描述
    structure: dict            # 抽象结构: {"元素A":"角色", "元素B":"角色", ...}
    candidate_domains: list[str]  # 候选类比域
    verified_cases: list[dict]    # [{"concept":"", "analogy":"", "score":5}]
    pitfalls: list[str]        # 常见错误


# ═══════════════════════════════════════
# 20条核心结构模式
# ═══════════════════════════════════════

PATTERNS = [
    # ── 过程/发展型 (5条) ──
    AnalogyPattern(
        pattern_id="process-linear",
        pattern_type="线性过程",
        description="起点(空洞)→ 中间步骤(填充)→ 终点(完满)。终态的本质依赖于整个过程的展开。",
        structure={"起点": "初始状态(空洞/模糊)", "过程": "逐步展开的步骤", "终点": "完满状态(本质显现)"},
        candidate_domains=["建筑工程", "烹饪", "种子生长", "编程编译", "旅行"],
        verified_cases=[
            {"concept": "黑格尔真理是全体", "analogy": "造桥合龙——之前只是构件，合龙那一步才成为桥", "score": 4},
        ],
        pitfalls=["容易只描述起点和终点而忽略过程的必要性", "过度强调终态而弱化了黑格尔的核心——过程即本质"],
    ),
    AnalogyPattern(
        pattern_id="process-iterative",
        pattern_type="迭代收敛",
        description="反复尝试→逐渐逼近→最终收敛。每次迭代都修正上一次的偏差。",
        structure={"初始猜测": "第一次尝试", "反馈循环": "纠正偏差的机制", "收敛结果": "逼近最优解"},
        candidate_domains=["机器学习调参", "写作文改稿", "射箭校准", "GPS导航重算"],
        verified_cases=[],
        pitfalls=["不要把收敛过程描述为直线前进", "需要强调每次迭代都改变了后续方向"],
    ),
    AnalogyPattern(
        pattern_id="process-dialectic",
        pattern_type="辩证运动",
        description="正题→反题→合题。冲突和对立不是错误，是推进的动力。",
        structure={"正题": "初始观点", "反题": "对立观点", "合题": "融合后的新理解"},
        candidate_domains=["辩论", "庭审", "科学争论", "设计迭代"],
        verified_cases=[],
        pitfalls=["不要把反题描述为'错误'——它是必要阶段", "合题不是妥协，是层次提升"],
    ),
    AnalogyPattern(
        pattern_id="process-emergent",
        pattern_type="涌现生成",
        description="大量简单组件按局部规则互动→宏观涌现出复杂有序行为。微观个体不知道整体在做什么。",
        structure={"微观组件": "简单个体", "局部规则": "个体行为的简单逻辑", "宏观涌现": "不可预测的复杂整体"},
        candidate_domains=["蚁群", "股市", "交通流", "神经网络"],
        verified_cases=[],
        pitfalls=["类比源太复杂会适得其反", "需要解释'为什么微观简单会导致宏观复杂'而不只是展示现象"],
    ),
    AnalogyPattern(
        pattern_id="process-cycle",
        pattern_type="循环往复",
        description="循环中的每个阶段都依赖上一个阶段的输出，回到起点时状态已改变。",
        structure={"阶段A": "第一环节", "阶段B": "第二环节", "反馈": "B的输出影响A的下一轮"},
        candidate_domains=["水循环", "经济周期", "生态系统", "产品迭代"],
        verified_cases=[],
        pitfalls=["避免让循环看起来像原地转圈", "需要在类比中显示'每次循环系统都往某个方向演变'"],
    ),

    # ── 约束/取舍型 (4条) ──
    AnalogyPattern(
        pattern_id="tradeoff-trilemma",
        pattern_type="三选二约束",
        description="三个目标不能同时最大化，最多满足两个，必须牺牲一个。",
        structure={"目标A": "第一个需要", "目标B": "第二个需要", "目标C": "第三个需要", "约束": "最多同时满足两个"},
        candidate_domains=["项目管理铁三角", "选车(快/省油/便宜)", "择业(高薪/轻松/有意义)"],
        verified_cases=[
            {"concept": "CAP定理", "analogy": "三人小组跨城协作，电话中断时必须选择：一致看同一版本(C)还是各自继续工作(A)", "score": 5},
        ],
        pitfalls=["三个要素如果用太相似的比喻会混淆", "类比必须让读者自己推导出'必须牺牲一个'的结论"],
    ),
    AnalogyPattern(
        pattern_id="tradeoff-diminishing",
        pattern_type="边际递减",
        description="每增加一单位投入，新增的收益逐渐减少。第一口最甜。",
        structure={"投入": "消耗的资源", "产出": "获得的回报", "递减曲线": "产出/投入比下降"},
        candidate_domains=["吃自助餐", "喝水解渴", "刷短视频", "加班效率"],
        verified_cases=[],
        pitfalls=["需要澄清'总收益仍在增加只是增量在减少'", "递减不等于负增长"],
    ),
    AnalogyPattern(
        pattern_id="tradeoff-threshold",
        pattern_type="阈值触发",
        description="量变积累到临界点→质变发生。在阈值之前看不出来，触发后不可逆。",
        structure={"量变阶段": "微小的累积变化", "临界点": "转折点", "质变": "突变的新状态"},
        candidate_domains=["水烧开", "压垮骆驼的稻草", "核链式反应", "网络效应临界质量"],
        verified_cases=[],
        pitfalls=["临界点不要太物理化——心理/社会领域的阈值概念需要不同类比", "不要留下'可以精确预测临界点'的印象"],
    ),
    AnalogyPattern(
        pattern_id="tradeoff-opportunity_cost",
        pattern_type="机会成本",
        description="选择一个意味着放弃另一个可能的价值。成本不仅是花掉的，也是没赚到的。",
        structure={"已选": "当前决策", "放弃": "次优选项的价值", "成本": "已选 + 放弃的总价值"},
        candidate_domains=["择校", "换工作", "买房还是租房", "时间分配"],
        verified_cases=[],
        pitfalls=["容易和沉没成本混淆", "类比需要展示'看不见的成本比看得见的大'"],
    ),

    # ── 层级/嵌套型 (4条) ──
    AnalogyPattern(
        pattern_id="hierarchy-abstraction",
        pattern_type="抽象层级",
        description="表层(具体现象)→中层(规则/模式)→深层(本质原理)。每层之上看不到下层。",
        structure={"表层": "可见的行为/现象", "中层": "支配表层的规则", "深层": "解释规则的根本原理"},
        candidate_domains=["冰山", "洋葱", "操作系统(UI→内核→硬件)"],
        verified_cases=[],
        pitfalls=["不要让中层和深层看起来是同一回事", "冰山类比已过度使用，优先用操作系统或洋葱"],
    ),
    AnalogyPattern(
        pattern_id="hierarchy-composition",
        pattern_type="部分-整体",
        description="整体的性质不能还原为部分的性质之和。离开了整体，部分失去意义。",
        structure={"部分": "组成元素", "整体": "大于部分之和的系统", "涌现属性": "仅在整体层面出现"},
        candidate_domains=["拼图(每块没有独立画面)", "乐队(单人无法演奏交响乐)", "球队"],
        verified_cases=[],
        pitfalls=["不要把'部分失去意义'极端化——手离开身体仍有生物学特征", "关键是要传达'整体提供了部分不具备的语境'"],
    ),
    AnalogyPattern(
        pattern_id="hierarchy-nesting",
        pattern_type="嵌套结构",
        description="结构内部包含同类型的子结构，无限或有限递归。每一层都是自相似的。",
        structure={"外层": "包含子结构的主结构", "内层": "结构相同但尺度更小的子结构"},
        candidate_domains=["俄罗斯套娃", "分形", "公司→部门→小组", "文件夹→子文件夹→文件"],
        verified_cases=[],
        pitfalls=["如果概念是有限嵌套，需要在类比中明确终止条件", "不要诱导读者认为所有结构都是无限嵌套的"],
    ),
    AnalogyPattern(
        pattern_id="hierarchy-network",
        pattern_type="网络结构",
        description="节点之间相互连接，间接影响通过多跳路径传播。关键是连接关系而非节点本身。",
        structure={"节点": "实体", "连接": "关系", "网络效应": "间接影响"},
        candidate_domains=["社交网络", "互联网路由", "食物链", "供应链"],
        verified_cases=[],
        pitfalls=["不要把网络类比成树（树无回路，网络有）", "间接影响比直接连接更难类比"],
    ),

    # ── 判断/标准型 (4条) ──
    AnalogyPattern(
        pattern_id="criterion-multi",
        pattern_type="多维度判断",
        description="一个对象必须同时满足多个独立条件才有资格。缺一不可。",
        structure={"条件A": "必要条件1", "条件B": "必要条件2", "条件C": "必要条件3", "判定": "必须全部满足"},
        candidate_domains=["比赛资格", "签证审核", "菜品评分", "新车验收"],
        verified_cases=[
            {"concept": "专利法三性", "analogy": "创新大赛评委用三个标准筛选：是否前所未有、是否比现有更巧妙、是否能实际制造", "score": 5},
        ],
        pitfalls=["不要暗示条件之间有替代关系", "三个条件如果太接近容易让读者分不清"],
    ),
    AnalogyPattern(
        pattern_id="criterion-compare",
        pattern_type="相对标准",
        description="判断不是绝对的，而是相对于参照物的。标准本身也在变化。",
        structure={"被判断": "目标对象", "参照物": "比较基准", "相对性": "标准随参照物变化"},
        candidate_domains=["体育比赛排名", "身高(在幼儿园/篮球队不同)", "房价(城市间比较)"],
        verified_cases=[],
        pitfalls=["不要把相对误解为'无所谓'", "需要保留'虽相对但有客观成分'的平衡"],
    ),
    AnalogyPattern(
        pattern_id="criterion-sufficient",
        pattern_type="充分必要条件",
        description="A发生时B一定发生(充分)，B发生时A一定先发生(必要)。区分充要/仅充分/仅必要。",
        structure={"充分条件": "有此即可", "必要条件": "无此不可", "充要": "缺一不可且独一即可"},
        candidate_domains=["钥匙和锁", "考试及格线", "驾照考试"],
        verified_cases=[],
        pitfalls=["这是最容易混淆的概念之一，类比必须极其清晰", "用日常例子(如驾照)比用逻辑符号更有效"],
    ),
    AnalogyPattern(
        pattern_id="criterion-falsification",
        pattern_type="可证伪性",
        description="一个命题必须有被证明为错的可能性，才是有意义的科学命题。不能证伪=无法检验。",
        structure={"命题": "待验证的声称", "证伪路径": "什么情况可以证明它是错的", "无证伪路径": "不可检验→非科学"},
        candidate_domains=["罪犯不在场证明", "天气预报", "药物效果测试"],
        verified_cases=[],
        pitfalls=["不要把'不可证伪'等同于'错误'——它只是不可检验", "需要区分'目前不能证伪'和'原则上不能证伪'"],
    ),

    # ── 互动/反馈型 (3条) ──
    AnalogyPattern(
        pattern_id="feedback-positive",
        pattern_type="正反馈",
        description="A增加→B增加→A进一步增加。雪球越滚越大，方向一致时相互强化。",
        structure={"触发": "初始变化", "放大": "正向循环", "结果": "指数级增长或崩溃"},
        candidate_domains=["银行挤兑", "网红传播", "股市泡沫", "话筒啸叫"],
        verified_cases=[],
        pitfalls=["不要把正反馈等同于'好事'", "清晰区分'放大器是什么'和'被放大的是什么'"],
    ),
    AnalogyPattern(
        pattern_id="feedback-negative",
        pattern_type="负反馈",
        description="A偏离目标→B产生反向力→A被拉回。恒温器不停调整，维持稳定。",
        structure={"设定值": "目标状态", "偏离": "实际与目标的差距", "修正": "反向调整力"},
        candidate_domains=["空调恒温", "人体体温", "自动巡航", "央行利率调控"],
        verified_cases=[],
        pitfalls=["不要把负反馈描述为'拖后腿'", "需要展示持续动态调整的过程而非一次修正"],
    ),
    AnalogyPattern(
        pattern_id="feedback-invisible_hand",
        pattern_type="无形协调",
        description="大量个体只追求自身利益→不需要中央规划→集体结果自动涌现出效率。",
        structure={"个体动机": "自利行为", "中间机制": "价格信号/竞争", "集体结果": "资源配置效率"},
        candidate_domains=["市场经济", "蚁群觅食", "开源社区", "交通自组织"],
        verified_cases=[],
        pitfalls=["需要说明'不总是有效'的条件", "市场失灵的情况也是类比边界的一部分"],
    ),
]


def search_patterns(concept_type: str = None, keyword: str = None) -> list[AnalogyPattern]:
    """搜索匹配的类比结构模式"""
    results = []
    for p in PATTERNS:
        if concept_type and p.pattern_type != concept_type:
            continue
        if keyword:
            if keyword.lower() in p.description.lower() or \
               any(keyword.lower() in d.lower() for d in p.candidate_domains):
                results.append(p)
            continue
        results.append(p)
    return results if (concept_type or keyword) else PATTERNS


def get_pattern_by_id(pattern_id: str) -> Optional[AnalogyPattern]:
    for p in PATTERNS:
        if p.pattern_id == pattern_id:
            return p
    return None


def format_patterns_for_prompt(patterns: list[AnalogyPattern]) -> str:
    """将结构模式格式化为可注入 LLM prompt 的文本"""
    lines = ["## 类比结构模式参考（选择最适合的一条使用）", ""]
    for p in patterns[:5]:  # 最多推荐5条
        lines.append(f"### {p.pattern_id}: {p.pattern_type}")
        lines.append(f"结构: {p.description}")
        lines.append(f"候选类比域: {', '.join(p.candidate_domains[:5])}")
        if p.verified_cases:
            lines.append(f"已验证案例: {p.verified_cases[0]['analogy']}")
        lines.append(f"避坑: {'; '.join(p.pitfalls[:2])}")
        lines.append("")
    return "\n".join(lines)
