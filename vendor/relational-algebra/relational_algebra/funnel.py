"""
漏斗降维路由器 — Funnel Dimension Reducer
==========================================

哲学原型：
  「由大到小，把外部的复杂锤碎装进瓶子」
  — 从辐射态坍缩进稳定态，用空间换时间

数学模型：
  Functor F: C(source) → C(target)
  - source: 高维辐射域（多元、分散、发散）
  - target: 低维稳定态（聚合、收敛、入瓶）
  - 漏斗壁 = 自然变换的自然性条件

核心直觉：
  - 输入是「无限多的数量堆砌」→ 通过筛选条件（税务/效率筛选）
  - 输出是「高效率的质量」→ 唯一稳定态
  - 路径 = 时间切片序列，每个切片控制「火烧热了」的接触火候
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import math

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')


@dataclass(frozen=True)
class FunnelSlice(Generic[T]):
    """
    时间切片：一个漏斗层级的输入/输出对

    - aperture: 开口大小（开口越大，能进入的候选越多）
    - candidates: 本层候选集合
    - survivors: 通过本层筛选的幸存者
    - compression_ratio: 压缩比 = len(survivors) / len(candidates)
    """
    layer: int
    aperture: float  # [0, 1]，1=全开，0=全闭
    candidates: tuple[T, ...]
    survivors: tuple[T, ...]
    compression_ratio: float

    def is_stable(self, threshold: float = 0.001) -> bool:
        """若压缩比低于阈值，视为已达稳定态"""
        return self.compression_ratio < threshold


class FunnelPolicy(ABC):
    """
    漏斗策略抽象 — 控制「火烧热了」的接触方式

    三种策略：
    1. TaxPolicy — 税务筛选：有能力的多纳税，没能力的淘汰
    2. RadiationPolicy — 辐射坍缩：越靠近中心越容易存活
    3. FractalPolicy — 分形复制：每个幸存者自我分裂再进入下一层
    """

    @abstractmethod
    def filter(self, candidates: tuple[T, ...], aperture: float) -> tuple[T, ...]:
        """给定候选集和开口大小，返回筛选结果"""
        ...

    @abstractmethod
    def aperture_schedule(self, layer: int, total_layers: int) -> float:
        """
        时间节点规划：第layer层的开口大小

        漏斗原则：从大到小，层数越高开口越小
        公式：aperture = 1 - (layer / total_layers) * (1 - min_aperture)
        """
        min_aperture: float = 0.05
        return max(min_aperture, 1.0 - (layer / total_layers) * (1.0 - min_aperture))


class TaxPolicy(FunnelPolicy):
    """
    税务筛选策略

    核心直觉：
      「有能力的人都赚了很多钱，然后把税务都交上来了」
      → 能力值越高，通过率越高
      → 最终剩下的是「最强的有能力的」
    """

    def __init__(self, ability_fn: Callable[[T], float], tax_rate: float = 0.3):
        self.ability_fn = ability_fn  # T -> ability_score [0, 1]
        self.tax_rate = tax_rate      # 税率，越高=筛选越严

    def filter(self, candidates: tuple[T, ...], aperture: float) -> tuple[T, ...]:
        if not candidates:
            return ()
        threshold = self._ability_threshold(aperture)
        return tuple(c for c in candidates if self.ability_fn(c) >= threshold)

    def aperture_schedule(self, layer: int, total_layers: int) -> float:
        # 开口 = 漏斗壁的「接触面积」
        # 火候控制：越深层越严
        base = super().aperture_schedule(layer, total_layers)
        return base * (1.0 - self.tax_rate * (layer / total_layers))

    def _ability_threshold(self, aperture: float) -> float:
        # 开口大 → 阈值低（让更多候选人进来）
        # 开口小 → 阈值高（只留精英）
        return (1.0 - aperture) * self.tax_rate


class RadiationPolicy(FunnelPolicy):
    """
    辐射坍缩策略

    核心直觉：
      「外部的东西装进去」
      → 每个候选者有「距离中心的位置」
      → 越近中心越容易通过筛选
    """

    def __init__(self, center_fn: Callable[[T], float]):
        self.center_fn = center_fn  # T -> distance_to_center [0, +inf]

    def filter(self, candidates: tuple[T, ...], aperture: float) -> tuple[T, ...]:
        if not candidates:
            return ()
        max_distance = self._max_distance(aperture)
        return tuple(c for c in candidates if self.center_fn(c) <= max_distance)

    def aperture_schedule(self, layer: int, total_layers: int) -> float:
        # 越深层 = 辐射半径越小 = 越接近核心
        base = super().aperture_schedule(layer, total_layers)
        return base

    def _max_distance(self, aperture: float) -> float:
        # aperture=1 → 无限远（所有人都进来）
        # aperture=0 → 0（只有中心的能进来）
        return aperture / max(1e-9, 1.0 - aperture)


class FractalPolicy(FunnelPolicy):
    """
    分形复制策略

    核心直觉：
      「用分型算法来制取它自我来找到它的残差偏移量」
      → 每个幸存者在下一层分裂成多个副本
      → 副本之间有微小的「偏移量」
      → 不是自我释放 = 残差偏移；是自我释放 = 完美复制
    """

    def __init__(self, split_fn: Callable[[T], List[T]], mutation_rate: float = 0.01):
        self.split_fn = split_fn    # T -> [T, T, ...]
        self.mutation_rate = mutation_rate  # 偏移量

    def filter(self, candidates: tuple[T, ...], aperture: float) -> tuple[T, ...]:
        # 第一步：每个候选者分裂
        children: List[T] = []
        for c in candidates:
            children.extend(self.split_fn(c))
        # 第二步：突变（给偏移量）
        # 第三步：通过开口筛选
        return self._apply_mutation(tuple(children), aperture)

    def _apply_mutation(
        self, candidates: tuple[T, ...], aperture: float
    ) -> tuple[T, ...]:
        if not candidates:
            return ()
        # 简单实现：假设T有__hash__，用hash模拟偏移量筛选
        threshold = int(aperture * 2**32)
        return tuple(
            c for c in candidates
            if hash(c) % (2**32) < threshold
        )

    def aperture_schedule(self, layer: int, total_layers: int) -> float:
        # 分形漏斗：每一层开口先大后小（先分裂再筛选）
        if layer < total_layers // 2:
            return 0.9  # 分裂阶段，开口大
        return 1.0 - (layer / total_layers) * 0.95


class FunnelReductor(Generic[T, R]):
    """
    漏斗降维器 — 将高维多元态压缩为低维稳定态

    使用示例：
        funnel = FunnelReductor(
            policy=TaxPolicy(ability_fn=lambda x: x['score']),
            total_layers=5,
        )
        result = funnel.reduce(candidates=users, bottleneck=extract_top_talent)
    """

    def __init__(
        self,
        policy: FunnelPolicy,
        total_layers: int = 5,
        on_slice: Optional[Callable[[FunnelSlice[T]], None]] = None,
    ):
        self.policy = policy
        self.total_layers = total_layers
        self.on_slice = on_slice  # 回调：每层完成后调用（火候观察）

    def reduce(
        self,
        candidates: List[T],
        bottleneck: Callable[[tuple[T, ...]], R],
    ) -> R:
        """
        执行漏斗降维

        Args:
            candidates: 初始候选集合（来自外界的复杂多元态）
            bottleneck: 瓶颈函数，最后一层调用的汇聚函数

        Returns:
            汇聚结果（R = 瓶子里的东西）
        """
        current: tuple[T, ...] = tuple(candidates)

        for layer in range(self.total_layers):
            aperture = self.policy.aperture_schedule(layer, self.total_layers)
            survivors = self.policy.filter(current, aperture)
            compression = (
                len(survivors) / len(current)
                if current else 0.0
            )

            slice_obj = FunnelSlice(
                layer=layer,
                aperture=aperture,
                candidates=current,
                survivors=survivors,
                compression_ratio=compression,
            )

            if self.on_slice:
                self.on_slice(slice_obj)

            if slice_obj.is_stable():
                # 已达稳定态，提前退出
                break

            current = survivors

        return bottleneck(current)

    def trace(self, candidates: List[T]) -> List[FunnelSlice[T]]:
        """返回完整的漏斗轨迹（用于可视化）"""
        trace: List[FunnelSlice[T]] = []
        self.reduce(candidates, bottleneck=lambda _: None)
        return trace


def default_bottleneck(items: tuple) -> Any:
    """
    默认瓶颈函数：返回唯一稳定态

    哲学对应：
      「最后坍缩成为唯一的那一个点」
      → 如果只剩一个，直接返回
      → 如果有多个，返回聚合态
    """
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    # 多于一个 → 夫妻共同体融合态
    return items


# ─────────────────────────────────────────────
# 漏斗编译器：把漏斗描述编译成执行计划
# ─────────────────────────────────────────────

@dataclass
class FunnelStage:
    name: str
    policy: str
    aperture: float
    filter_fn: Optional[str] = None  # 函数名（序列化用）


@dataclass
class FunnelPlan:
    stages: List[FunnelStage]
    bottleneck_fn: str
    description: str


def compile_funnel_plan(
    policy_names: List[str],
    total_layers: int,
    bottleneck_fn: str = "default_bottleneck",
) -> FunnelPlan:
    """
    编译漏斗执行计划

    用于序列化/存储/跨语言传输漏斗配置
    """
    stages = []
    for i, pol in enumerate(policy_names):
        aperture = 1.0 - (i / total_layers) * 0.95
        stages.append(FunnelStage(
            name=f"layer_{i}",
            policy=pol,
            aperture=round(aperture, 4),
        ))
    return FunnelPlan(
        stages=stages,
        bottleneck_fn=bottleneck_fn,
        description=f"漏斗降维计划，共{len(stages)}层",
    )


if __name__ == "__main__":
    # 演示：税务筛选漏斗
    users = [
        {"name": f"user_{i}", "score": (i % 10) / 10.0}
        for i in range(100)
    ]

    def top_talent(items: tuple) -> dict:
        return {"top_talent": list(items[-10:])}

    funnel = FunnelReductor(
        policy=TaxPolicy(ability_fn=lambda u: u["score"], tax_rate=0.2),
        total_layers=5,
        on_slice=lambda s: print(
            f"  Layer {s.layer}: aperture={s.aperture:.3f}, "
            f"in={len(s.candidates)}, out={len(s.survivors)}, "
            f"ratio={s.compression_ratio:.3f}"
        ),
    )

    print("税务筛选漏斗执行轨迹：")
    result = funnel.reduce(users, bottleneck=top_talent)
    print(f"\n最终结果：{result}")
