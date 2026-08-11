# relational_algebra — 主体间关系代数 Python 实现
# =============================================

"""
主体间关系代数 · 关系代数 · 主体间协议 · 认知隔离舱 · 漏斗降维 · 单子融合

核心模块：
  core              — 关系代数核心（选择/投影/连接/并/差）
  cognitive_isolation — 认知隔离舱（多元生命体架构）
  perception_bus    — 全感知模态总线
  memory_point      — 全感知模态记忆点
  narrow_waist_ir   — 漏斗式几何范畴窄腰 IR
  funnel_frontend   — 漏斗前端（将复杂输入映射为窄腰操作）
  bootstrap_compiler — 自举编译器
  phase_analyzer    — 认知相位分析器
  attribution       — 归属引擎
  funnel            — 漏斗降维路由器（由大到小，空间换时间）
  observer          — 认知观测者（二阶观测/三元裁判/有无转换）
  monoidal          — 单子单位元（夫妻共同体/满全法/月全食）
  phase_router      — 相位路由器（时间切片/火候控制/动态推进）
  ai_architecture  — AI架构关系代数化（Transformer/Mamba/RWKV对照/改造路线图）
  four_dimensional — 四维认知框架（0D有无/1D时间/2D博弈/3D裁判/4D镜像空间）
  binary_system    — 254二进制统计系统（阴+阳+254容器=256/间接存在/最省力估算）

协议版本：1.0.0
许可证：BSD-3-Clause-Interpersonal（主体间关系修改版）
"""

__version__ = "0.1.0"
__author__ = "莫刘连理萝莉兰零离 <lolict@outlook.com>"
__license__ = "BSD-3-Clause-Interpersonal"

from relational_algebra.core import Relation
from relational_algebra.core_compat import (
    selection,
    projection,
    natural_join,
    union,
    difference,
    SemiJoin,
)

from relational_algebra.attribution import (
    AttributionEngine,
    AttributionReport,
)

from relational_algebra.funnel import (
    FunnelReductor,
    FunnelPolicy,
    TaxPolicy,
    RadiationPolicy,
    FractalPolicy,
    FunnelSlice,
    compile_funnel_plan,
)

from relational_algebra.observer import (
    CognitiveObserver,
    ExistenceObserver,
    CapacityObserver,
    TripleJudgment,
    ObserverState,
    JudgmentFlow,
    AlignmentType,
    )

from relational_algebra.monoidal import (
    FusionState,
    MonoidalIdentity,
    I,
    Entity,
    ManQuanFa,
    MonoidalFusionEngine,
    )

from relational_algebra.phase_router import (
    PhaseRouter,
    PhaseSlice,
    HeatControlPolicy,
    SlowHeatPolicy,
    FastContactPolicy,
    DynamicPromoter,
    PhaseType,
)

__all__ = [
    # 核心关系代数
    "Relation",
    "selection", "projection", "natural_join", "union", "difference", "SemiJoin",
    # 归属引擎
    "AttributionEngine", "AttributionReport", "ContributionType",
    # 漏斗
    "FunnelReductor", "FunnelPolicy", "TaxPolicy", "RadiationPolicy",
    "FractalPolicy", "FunnelSlice", "compile_funnel_plan",
    # 观测者
    "CognitiveObserver", "ExistenceObserver", "CapacityObserver",
    "TripleJudgment", "ObserverState", "JudgmentFlow", "AlignmentType",
    # 单子
    "MonoidalIdentity", "I", "Entity", "ManQuanFa", "MonoidalFusionEngine",
    # 相位路由
    "PhaseRouter", "PhaseSlice", "HeatControlPolicy", "SlowHeatPolicy",
    "FastContactPolicy", "DynamicPromoter", "PhaseType",
]
