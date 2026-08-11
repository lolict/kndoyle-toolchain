"""
相位路由器 — Phase Router
==========================

哲学原型：
  「控制时间的火候，就像火烧热了，你要用快速的方式去接触火」
  「时间控制和空间控制，在一个范畴内只做到让内存不溢出」
  「然后逐步的推动，动态的推动做成一件事情」

核心概念：
  - 时间切片（Phase Slice）：把连续时间切分成离散片
  - 相位路由（Phase Routing）：每片只做一件事，防止内存溢出
  - 火候控制：片与片之间的衔接节奏
  - 动态推进：从「一次性吃完」→ 「切片慢慢吃」
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, List, Any, Optional, Dict
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto
import time

T = TypeVar('T')
R = TypeVar('R')


class PhaseType(Enum):
    """相位类型"""
    WARMUP = auto()    # 热身/升温：准备资源
    ACTIVE = auto()    # 活跃：执行核心计算
    COOLDOWN = auto()  # 冷却：释放资源、存档结果
    IDLE = auto()      # 空闲：等待下一步输入
    OVERFLOW_PROTECT = auto()  # 防溢出：分布式转移任务


@dataclass
class PhaseSlice(Generic[T]):
    """
    时间切片

    包含：
      - index: 片编号（从0开始）
      - data: 片内数据
      - phase_type: 相位类型
      - duration_hint: 建议持续时间（秒）
      - memory_budget: 本片内存预算（字节）
    """
    index: int
    data: T
    phase_type: PhaseType
    duration_hint: float = 1.0
    memory_budget: int = 1024 * 1024  # 默认 1MB


@dataclass
class PhaseStats:
    """相位执行统计"""
    phase_type: PhaseType
    duration_actual: float
    memory_peak: int
    items_processed: int
    overflow_count: int = 0


class HeatControlPolicy(ABC):
    """
    火候控制策略

    控制「火烧热了」的接触方式
    """

    @abstractmethod
    def next_phase_duration(
        self,
        current_phase: PhaseType,
        heat_level: float,
    ) -> float:
        """给定当前相位和热度，返回下一片持续时间"""
        ...

    @abstractmethod
    def heat_update(
        self,
        current_heat: float,
        phase_result: Any,
    ) -> float:
        """根据相位执行结果更新热度"""
        ...


class SlowHeatPolicy(HeatControlPolicy):
    """
    慢热策略：先小后大，逐步升温

    适合：
      - 资源初始化
      - 用户体验平滑加载
    """

    def next_phase_duration(
        self,
        current_phase: PhaseType,
        heat_level: float,
    ) -> float:
        if heat_level < 0.3:
            return 0.1   # 微小片，快速启动
        elif heat_level < 0.7:
            return 0.5   # 中等片
        else:
            return 1.0   # 全速片

    def heat_update(
        self,
        current_heat: float,
        phase_result: Any,
    ) -> float:
        # 成功 → 升温，失败 → 降温
        if phase_result is not None:
            return min(1.0, current_heat + 0.1)
        return max(0.0, current_heat - 0.2)


class FastContactPolicy(HeatControlPolicy):
    """
    快接触策略：快速升温，快速冷却

    适合：
      - 瞬时任务
      - 事件驱动
    """

    def next_phase_duration(
        self,
        current_phase: PhaseType,
        heat_level: float,
    ) -> float:
        if current_phase == PhaseType.WARMUP:
            return 0.05  # 极快热身
        return 0.2      # 快速执行

    def heat_update(
        self,
        current_heat: float,
        phase_result: Any,
    ) -> float:
        if phase_result:
            return 1.0  # 立即达到峰值
        return 0.0     # 立即冷却


class PhaseRouter(Generic[T, R]):
    """
    相位路由器

    功能：
      1. 把输入数据切分成时间片
      2. 按火候策略控制每片节奏
      3. 防止内存溢出（溢出时分布式转移）
      4. 动态推进：片完成后决定下一步
    """

    def __init__(
        self,
        heat_policy: Optional[HeatControlPolicy] = None,
        max_memory_per_slice: int = 10 * 1024 * 1024,
        enable_overflow_protect: bool = True,
    ):
        self.heat_policy = heat_policy or SlowHeatPolicy()
        self.max_memory_per_slice = max_memory_per_slice
        self.enable_overflow_protect = enable_overflow_protect
        self.heat_level: float = 0.0
        self.stats: List[PhaseStats] = []
        self._overflow_buffer: List[Any] = []

    def route(
        self,
        data: List[T],
        processor: Callable[[PhaseSlice[T]], R],
        max_slices: Optional[int] = None,
    ) -> List[R]:
        """
        执行相位路由

        Args:
            data: 输入数据列表
            processor: 每片处理器
            max_slices: 最大片数（防止无限循环）

        Returns:
            每片的处理结果列表
        """
        results = []
        remaining = list(data)
        slice_index = 0

        while remaining:
            # 决定片大小（防止内存溢出）
            slice_data = self._allocate_slice(remaining)
            phase_type = self._phase_type_for(slice_index, data)

            phase = PhaseSlice(
                index=slice_index,
                data=slice_data,
                phase_type=phase_type,
                duration_hint=self.heat_policy.next_phase_duration(
                    phase_type, self.heat_level
                ),
                memory_budget=self.max_memory_per_slice,
            )

            # 执行处理
            start = time.time()
            try:
                result = processor(phase)
            except MemoryError:
                result = self._handle_overflow(phase, processor)
            end = time.time()

            # 统计
            stats = PhaseStats(
                phase_type=phase_type,
                duration_actual=end - start,
                memory_peak=self._estimate_memory(slice_data),
                items_processed=len(slice_data),
            )
            self.stats.append(stats)

            # 更新热度
            self.heat_level = self.heat_policy.heat_update(
                self.heat_level, result
            )

            results.append(result)
            slice_index += 1

            if max_slices and slice_index >= max_slices:
                break

        return results

    def _allocate_slice(self, remaining: List[T]) -> List[T]:
        """分配下一片数据（防止内存溢出）"""
        if not remaining:
            return []

        # 简单策略：固定片大小
        # 复杂策略：根据当前内存压力动态调整
        slice_size = min(len(remaining), self._compute_slice_size())
        allocated = remaining[:slice_size]
        return allocated

    def _compute_slice_size(self) -> int:
        """根据内存预算计算片大小"""
        # 默认：每片处理100个元素
        base_size = 100
        if self.enable_overflow_protect:
            # 内存紧张时缩小片
            if self.heat_level > 0.9:
                return max(1, base_size // 4)
            elif self.heat_level > 0.7:
                return max(1, base_size // 2)
        return base_size

    def _phase_type_for(self, index: int, total: List[T]) -> PhaseType:
        """根据片位置决定相位类型"""
        progress = index / max(len(total), 1)
        if progress < 0.1:
            return PhaseType.WARMUP
        elif progress > 0.9:
            return PhaseType.COOLDOWN
        else:
            return PhaseType.ACTIVE

    def _handle_overflow(
        self,
        phase: PhaseSlice[T],
        processor: Callable[[PhaseSlice[T]], R],
    ) -> R:
        """内存溢出处理：分布式转移"""
        self._overflow_buffer.extend(phase.data)
        return processor(PhaseSlice(
            index=phase.index,
            data=[],
            phase_type=PhaseType.OVERFLOW_PROTECT,
            duration_hint=0.0,
        ))

    def _estimate_memory(self, data: List[T]) -> int:
        """估算数据内存占用（字节）"""
        try:
            import sys
            return sys.getsizeof(data)
        except Exception:
            return len(data) * 100  # 粗略估算

    def summary(self) -> Dict[str, Any]:
        """返回执行摘要"""
        if not self.stats:
            return {}
        return {
            "total_slices": len(self.stats),
            "total_duration": sum(s.duration_actual for s in self.stats),
            "total_items": sum(s.items_processed for s in self.stats),
            "overflow_events": sum(s.overflow_count for s in self.stats),
            "phase_distribution": {
                pt.name: sum(1 for s in self.stats if s.phase_type == pt)
                for pt in PhaseType
            },
        }


# ─────────────────────────────────────────────
# 动态推进器：替代「一次性吃完」的模式
# ─────────────────────────────────────────────

class DynamicPromoter:
    """
    动态推进器

    核心思路：
      把一个任务从「一次性执行」改为「分片推进」
      每片完成后决定：
        - 继续（CONTINUE）
        - 暂停（PAUSE）等待资源
        - 终止（DONE）完成任务
    """

    def __init__(self, router: PhaseRouter):
        self.router = router
        self.phase_results: List[Any] = []

    def promote(
        self,
        task: Callable[[], List[T]],
        process_fn: Callable[[PhaseSlice[T]], R],
        completion_check: Callable[[List[R]], bool],
    ) -> List[R]:
        """
        动态推进一个任务

        流程：
          1. 获取初始数据
          2. 执行相位路由
          3. 检查完成条件
          4. 若未完成 → 追加新数据 → 继续
        """
        results = []
        while True:
            data = task()  # 获取数据
            if not data:
                break

            batch_results = self.router.route(data, process_fn)
            results.extend(batch_results)

            if completion_check(results):
                break

        return results


if __name__ == "__main__":
    import random

    # 演示：把100个任务分片处理
    data = list(range(100))

    router = PhaseRouter(
        heat_policy=SlowHeatPolicy(),
        max_memory_per_slice=1024,
    )

    def process(phase: PhaseSlice[int]) -> dict:
        processed = [x * 2 for x in phase.data]
        return {"phase": phase.phase_type.name, "count": len(processed)}

    results = router.route(data, process, max_slices=10)

    print(f"处理了 {len(results)} 个片")
    print(f"执行摘要：{router.summary()}")
