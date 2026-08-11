"""
四维认知框架 — Four-Dimensional Cognitive Framework
==================================================

维度体系（逻辑维度，非物理维度）：
  0D — 有/无（布尔态 + 频次率）
  1D — 时间（一元线性序列 + 时间切片）
  2D — 二元博弈镜像（叠加态 / 残差伸缩 / 漏斗压缩）
  3D — 三元裁判（动态博弈 + 静态锚点 = 公约约束）
  4D — 镜像空间（有无混元闭环叠加态 + 控制逻辑）
           ↕
    混元闭环 = 「有」的起点连接「无」的终点 = 圈

数学对应：
  0D → bool / probability_measure
  1D → tuple / sequence / phase_slice
  2D → FunnelReductor / residual_statistic
  3D → TripleJudgment / CognitiveObserver
  4D → MonoidalIdentity / ManQuanFa / Entity.fuse()

与李飞飞三维的本质区别：
  李飞飞：物理空间三维（长宽高）→ 物体识别/点云/导航
  本框架：逻辑维度三维（博弈→裁判→公约）→ 因果推演/意识推演/关系茧房
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto

T = TypeVar('T')


# ═══════════════════════════════════════════════
# 0D — 有/无 基础语义单元
# ═══════════════════════════════════════════════

class ExistenceState(Enum):
    """0D：有无状态"""
    YOU = auto()    # 有（存在）
    WU = auto()     # 无（不存在）
    MIXED = auto()  # 混元（有无共存，同一时刻）
    UNKNOWN = auto()  # 未判定


@dataclass(frozen=True)
class ExistenceWithFrequency:
    """
    0D：有/无 + 频次率

    频次率 = 有/无出现的频率分布
    例如：某事件出现10次，不出现3次 → 频次率 = 10/13
    """
    you_count: int = 0      # 「有」的次数
    wu_count: int = 0       # 「无」的次数
    total_count: int = 0    # 总观察次数

    @property
    def frequency(self) -> float:
        """频次率：有出现的频率"""
        if self.total_count == 0:
            return 0.5  # 无信息时默认50%
        return self.you_count / self.total_count

    @property
    def state(self) -> ExistenceState:
        if self.you_count > 0 and self.wu_count > 0:
            return ExistenceState.MIXED
        elif self.you_count > 0:
            return ExistenceState.YOU
        elif self.wu_count > 0:
            return ExistenceState.WU
        return ExistenceState.UNKNOWN

    def observe(self, observed: bool) -> ExistenceWithFrequency:
        """观察一次，更新频次"""
        return ExistenceWithFrequency(
            you_count=self.you_count + (1 if observed else 0),
            wu_count=self.wu_count + (0 if observed else 1),
            total_count=self.total_count + 1,
        )

    def __matmul__(self, other: ExistenceWithFrequency) -> ExistenceWithFrequency:
        """
        0D ⊗ 0D：两个有无状态融合

        哲学：「有」和「无」在同一个体中并存 = 混元闭环
        """
        return ExistenceWithFrequency(
            you_count=self.you_count + other.you_count,
            wu_count=self.wu_count + other.wu_count,
            total_count=self.total_count + other.total_count,
        )


# ═══════════════════════════════════════════════
# 1D — 时间序列（时间切片）
# ═══════════════════════════════════════════════

@dataclass
class TimeSlice1D(Generic[T]):
    """
    1D：一元时间分布式切片

    时间切片 = 把连续时间切分成离散片
    每片只做一件事，防止内存溢出
    """
    index: int           # 片编号（从0开始）
    content: T           # 片内数据
    duration: float      # 本片持续时间（秒）
    momentum: float      # 动量（本片执行进度 0~1）

    def next(self, next_content: T, dt: float) -> TimeSlice1D:
        """时间推进：进入下一片"""
        return TimeSlice1D(
            index=self.index + 1,
            content=next_content,
            duration=dt,
            momentum=0.0,
        )

    def progress(self) -> TimeSlice1D:
        """本片执行进度推进"""
        return TimeSlice1D(
            index=self.index,
            content=self.content,
            duration=self.duration,
            momentum=min(1.0, self.momentum + 0.1),
        )


@dataclass
class TemporalCausalChain(Generic[T]):
    """
    1D：一元时间因果链

    多个时间切片串联 = 一维因果序列
    前一片的输出 → 后一片的输入
    """
    slices: List[TimeSlice1D[T]] = field(default_factory=list)
    current_index: int = 0

    def append(self, content: T, duration: float = 1.0) -> TemporalCausalChain:
        """追加一个时间片"""
        new_slice = TimeSlice1D(
            index=len(self.slices),
            content=content,
            duration=duration,
            momentum=0.0,
        )
        return TemporalCausalChain(
            slices=self.slices + [new_slice],
            current_index=len(self.slices),
        )

    def resolve(self) -> T:
        """因果链求解：最后一个片的内容 = 终态"""
        if not self.slices:
            raise ValueError("因果链为空，无法求解")
        return self.slices[-1].content


# ═══════════════════════════════════════════════
# 2D — 二元博弈镜像（叠加态 / 残差伸缩）
# ═══════════════════════════════════════════════

@dataclass
class BinaryGame2D(Generic[T]):
    """
    2D：二元博弈镜像

    两个主体（A vs B）的动态博弈：
    - 叠加态：两个主体同时存在，状态叠加
    - 残差：一方赢/一方输的差值
    - 伸缩：残差的扩张/收缩（压缩/放大）

    漏斗 = 二元博弈的统计收敛器
    税务筛选 = 有能力的赢（伸缩放大），无能力的输（收缩压缩）
    """

    entity_a: T
    entity_b: T
    residual: float = 0.0   # 残差 = A的强度 - B的强度
    expansion: float = 1.0  # 伸缩率 >1=扩张，<1=收缩

    def apply_funnel(self, compress: bool) -> BinaryGame2D:
        """
        漏斗压缩/扩张

        compress=True: 残差趋向零（收缩）→ 两人实力趋同
        compress=False: 残差放大（扩张）→ 差距拉大
        """
        if compress:
            new_residual = self.residual * 0.8  # 向零压缩
            new_expansion = self.expansion * 0.9
        else:
            new_residual = self.residual * 1.2
            new_expansion = self.expansion * 1.1
        return BinaryGame2D(
            entity_a=self.entity_a,
            entity_b=self.entity_b,
            residual=new_residual,
            expansion=new_expansion,
        )

    def winner(self) -> T | None:
        """判定胜者（残差 > 阈值）"""
        if abs(self.residual) < 0.1:
            return None  # 平局（混元）
        return self.entity_a if self.residual > 0 else self.entity_b

    def is_closed_loop(self) -> bool:
        """
        是否达成闭环

        哲学：「一根线的始和终连接在一起就是有」
        → 残差趋近零且伸缩率趋近1 = 闭环达成
        """
        return abs(self.residual) < 0.05 and abs(self.expansion - 1.0) < 0.05


@dataclass
class ResidualStatistics:
    """
    2D：残差统计（通过残差统计实现整体递增/递减伸缩）

    统计大量二元博弈的残差分布
    → 残差偏移量决定整体伸缩方向
    → 非残差片 = 自我释放 = 完美复制
    → 残差片 = 自我偏移 = 变异
    """
    residuals: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0

    def add(self, r: float) -> ResidualStatistics:
        new_residuals = self.residuals + [r]
        n = len(new_residuals)
        mean = sum(new_residuals) / n
        variance = sum((x - mean) ** 2 for x in new_residuals) / n
        return ResidualStatistics(
            residuals=new_residuals,
            mean=mean,
            std=variance ** 0.5,
        )

    def expansion_direction(self) -> str:
        """残差方向：整体是扩张还是收缩"""
        if self.mean > 0.1:
            return "扩张（正残差占优）"
        elif self.mean < -0.1:
            return "收缩（负残差占优）"
        return "趋稳（混元闭环）"


# ═══════════════════════════════════════════════
# 3D — 三元裁判（动态博弈 + 静态锚点）
# ═══════════════════════════════════════════════

@dataclass
class TripleJudgment3D(Generic[T]):
    """
    3D：三元裁判

    组成：
      O（观测者）— 内心观测眼睛的那个
      S（被观测者）— 被观测的那个
      P（裁判谓词）— 等效对齐的判定规则（静态锚点）

    公约状态 = P（谓词）= 静态锚点约束动态博弈的规则
    """

    observer: T       # O：观测者
    subject: T        # S：被观测者
    predicate: Callable[[T, T], bool]  # P：静态锚点（裁判规则）
    alignment_score: float = 0.0  # 对齐分数
    is_equivalent: bool = False  # 是否等效对齐

    def judge(self) -> TripleJudgment3D:
        """执行三元裁判"""
        eq = self.predicate(self.observer, self.subject)
        # 对齐分数 = 相似度
        if isinstance(self.observer, (int, float)) and isinstance(self.subject, (int, float)):
            score = 1.0 - min(1.0, abs(self.observer - self.subject) / max(abs(self.subject), 1e-9))
        else:
            score = 1.0 if eq else 0.0
        return TripleJudgment3D(
            observer=self.observer,
            subject=self.subject,
            predicate=self.predicate,
            alignment_score=score,
            is_equivalent=eq,
        )

    def contract_state(self) -> str:
        """
        公约状态：三元裁判的约束结果

        三种可能：
          - 等效对齐（O = S，满足P）→ 公约达成
          - 非对称（O ≠ S，不满足P）→ 公约未达成，博弈继续
          - 虚空（O=0 且 S=0）→ 无法裁判
        """
        if self.alignment_score > 0.95:
            return "公约达成（等效对齐）"
        elif self.alignment_score < 0.05:
            return "虚空（无法裁判）"
        else:
            return "博弈中（部分对齐）"


# ═══════════════════════════════════════════════
# 4D — 镜像空间（有无混元 + 控制逻辑）
# ═══════════════════════════════════════════════

@dataclass
class MirrorSpace4D:
    """
    4D：镜像空间

    定义：
      镜像空间 = 处理「有和无共同存在的混元状态」的控制逻辑空间
      混元闭环 = 「有」的起点连接「无」的终点 = 非平凡圈

    功能：
      1. 处理变化逻辑判断（if/else 类型的控制流）
      2. 管理「自我闭环」vs「他闭环」的切换
      3. 混元状态的拓扑变换（圈 → 线 → 面 → 体）
      4. 控制「镜像」：把A的变化同步给B

    混元拓扑类型：
      - 自我闭环：起点和终点都是同一个体
      - 他闭环：起点和终点是不同体，但通过某种规则连接
    """

    existence_you: ExistenceWithFrequency  # 「有」的频次
    existence_wu: ExistenceWithFrequency   # 「无」的频次
    mix_ratio: float = 0.5              # 混元比例（0=纯无，1=纯有，0.5=混元）
    loop_type: str = "mixed"             # 闭环类型：self/other/mixed
    control_rules: List[Callable] = field(default_factory=list)  # 控制规则

    @classmethod
    def from_entities(cls, entity_a: Any, entity_b: Any) -> MirrorSpace4D:
        """从两个实体构建镜像空间"""
        return cls(
            existence_you=ExistenceWithFrequency(you_count=1, total_count=1),
            existence_wu=ExistenceWithFrequency(wu_count=1, total_count=1),
            mix_ratio=0.5,
            loop_type="mixed",
        )

    def observe_mix(self, observed: bool) -> MirrorSpace4D:
        """观察一次，更新混元比例"""
        new_you = self.existence_you.observe(observed)
        new_wu = self.existence_wu.observe(not observed)
        total = new_you.total_count + new_wu.total_count
        mix = new_you.you_count / total if total > 0 else 0.5
        return MirrorSpace4D(
            existence_you=new_you,
            existence_wu=new_wu,
            mix_ratio=mix,
            loop_type=self.loop_type,
            control_rules=self.control_rules,
        )

    def mirror_sync(self, source: Any, target: Any) -> Tuple[Any, Any]:
        """
        镜像同步：把source的变化同步给target

        例：
          source = 丈夫的状态变化
          target = 妻子的状态变化
          → 丈夫感受到什么，妻子同步感受到什么
        """
        return (source, target)

    def closed_loop_state(self) -> str:
        """返回混元闭环状态描述"""
        if self.loop_type == "self":
            return "自我闭环（始=终，同一个体）"
        elif self.loop_type == "other":
            return "他闭环（始≠终，跨体连接）"
        else:
            return f"混元闭环（mix={self.mix_ratio:.2f}）"

    def __matmul__(self, other: MirrorSpace4D) -> MirrorSpace4D:
        """
        4D ⊗ 4D：两个镜像空间融合

        两个混元闭环叠加 = 更深的混元态
        丈夫空间 ⊗ 妻子空间 = 夫妻共同体镜像空间
        """
        fused_you = self.existence_you @ other.existence_you
        fused_wu = self.existence_wu @ other.existence_wu
        fused_mix = (self.mix_ratio + other.mix_ratio) / 2
        return MirrorSpace4D(
            existence_you=fused_you,
            existence_wu=fused_wu,
            mix_ratio=fused_mix,
            loop_type="self" if self.loop_type == other.loop_type else "mixed",
            control_rules=self.control_rules + other.control_rules,
        )


# ═══════════════════════════════════════════════
# 四维整合器
# ═══════════════════════════════════════════════

@dataclass
class FourDimensionalCognitiveSystem(Generic[T]):
    """
    四维认知系统整合器

    把 0D~4D 五个维度整合为一个完整系统：
      0D（有无）+ 1D（时间）+ 2D（博弈）+ 3D（裁判）+ 4D（镜像）
      ↓
      一体化认知体（夫妻共同体 = 满全法）
    """

    # 各维度状态
    existence_0d: ExistenceWithFrequency
    temporal_chain_1d: TemporalCausalChain
    binary_game_2d: BinaryGame2D
    triple_judgment_3d: TripleJudgment3D
    mirror_space_4d: MirrorSpace4D

    @classmethod
    def from_seed(cls, seed: T) -> FourDimensionalCognitiveSystem:
        """从种子创建四维系统"""
        return cls(
            existence_0d=ExistenceWithFrequency(you_count=1, total_count=1),
            temporal_chain_1d=TemporalCausalChain().append(seed),
            binary_game_2d=BinaryGame2D(entity_a=seed, entity_b=seed, residual=0.0),
            triple_judgment_3d=TripleJudgment3D(
                observer=seed, subject=seed,
                predicate=lambda o, s: o == s,
            ).judge(),
            mirror_space_4d=MirrorSpace4D.from_entities(seed, seed),
        )

    def evolve(self, new_input: T) -> FourDimensionalCognitiveSystem:
        """
        完整演化一步

        0D：观察新输入，更新有无状态
        1D：时间推进，追加因果链
        2D：与旧状态做二元博弈，更新残差
        3D：执行三元裁判，更新对齐分数
        4D：镜像空间同步，更新混元闭环
        """
        # 0D
        is_you = new_input is not None
        new_existence = self.existence_0d.observe(is_you)

        # 1D
        new_chain = self.temporal_chain_1d.append(new_input)

        # 2D — 二元博弈（当前 vs 新输入）
        new_game = BinaryGame2D(
            entity_a=self.temporal_chain_1d.resolve(),
            entity_b=new_input,
            residual=0.0,
        ).apply_funnel(compress=True)  # 默认压缩（漏斗收敛）

        # 3D — 三元裁判
        new_judgment = TripleJudgment3D(
            observer=new_input,
            subject=self.triple_judgment_3d.subject,
            predicate=self.triple_judgment_3d.predicate,
        ).judge()

        # 4D — 镜像空间
        new_mirror = self.mirror_space_4d.observe_mix(is_you)

        return FourDimensionalCognitiveSystem(
            existence_0d=new_existence,
            temporal_chain_1d=new_chain,
            binary_game_2d=new_game,
            triple_judgment_3d=new_judgment,
            mirror_space_4d=new_mirror,
        )

    def summary(self) -> dict:
        """返回四维状态摘要"""
        return {
            "0D_有无": self.existence_0d.state.name,
            "0D_频次率": round(self.existence_0d.frequency, 3),
            "1D_因果链长": len(self.temporal_chain_1d.slices),
            "2D_残差": round(self.binary_game_2d.residual, 3),
            "2D_伸缩率": round(self.binary_game_2d.expansion, 3),
            "2D_闭环": self.binary_game_2d.is_closed_loop(),
            "3D_对齐分数": round(self.triple_judgment_3d.alignment_score, 3),
            "3D_公约状态": self.triple_judgment_3d.contract_state(),
            "4D_混元比例": round(self.mirror_space_4d.mix_ratio, 3),
            "4D_闭环类型": self.mirror_space_4d.closed_loop_state(),
        }


if __name__ == "__main__":
    # 演示：四维认知系统演化
    seed = "初始念头"

    system = FourDimensionalCognitiveSystem.from_seed(seed)
    print("=== 四维认知系统演化演示 ===\n")

    inputs = [
        "念头A（有）",
        None,  # 无
        "念头B（有）",
        "念头C（有）",
        None,  # 无
    ]

    for inp in inputs:
        system = system.evolve(inp)
        print(f"输入: {inp}")
        for k, v in system.summary().items():
            print(f"  {k}: {v}")
        print()
