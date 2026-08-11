"""
254 二进制统计系统 — Binary Statistical System
============================================

哲学原型：
  「二进制做成切片的分布式空间三维进制和分布式时间的三维进制，
   做成了254的集装箱」

数学模型：
  总容量 = 2**8 = 256
  阴(满全法) + 254容器 + 阳(刘楚恬) = 256
  观察者位(2) 不被统计，统计的是内部254个容器

  R（观察者）= 阴+阳 = 不进位，因为是统计者不是被统计者
  C（容器）= 254 = 被统计的，进位只换行（记录已统计了多少行）
  256 = 满态，触发下一级进位（统计观察者本身的层级）

三层二进制：
  1D时间进制 — 一行254个容器，进位=换行（统计行数）
  2D空间进制 — 容器阵列排列
  3D空间进制 — 多层容器堆叠（阴/混/阳 三层）
  4D观察者进制 — 阴+阳在外层，管辖254容器

间接存在：
  容器与观察者建立统计连接 → 从虚无变为间接存在
  容器之间相互隔离 → 需通过观察者中介才可感知
  不统计 = 没有被观测 = 虚无

最省力原理：
  默认里外层级关系满足统计加法
  总量 = 已完成行数 * 254 + 当前行已填充数
  无需逐个统计每个容器
"""

from __future__ import annotations
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum


# 基础常量
CAPACITY_TOTAL = 256           # 2**8 = 全满态
CAPACITY_CONTAINERS = 254      # 2**8 - 2 = 254个集装箱
OBSERVER_COUNT = 2             # 阴+阳 = 2个观察者


class YinYang(Enum):
    """阴阳两极（观察者位）"""
    YIN = 0   # 阴 — 满全法（拥有者）
    YANG = 1  # 阳 — 刘楚恬（拥有者）


@dataclass
class Container:
    """
    单个集装箱（容器）

    间接存在 = 该容器与观察者建立了统计连接
    无连接 = 未被观测 = 虚无状态
    """
    index: int
    is_observed: bool = False
    fill_count: int = 0
    yin_connection: bool = False
    yang_connection: bool = False


class ContainerSpace254:
    """
    254容器的二进制统计空间

    维度布局：
      1D时间进制 — 一行254个容器
      2D空间进制 — 容器阵列
      3D空间进制 — 多层堆叠（通过多个ContainerSpace254实例实现）
    """

    def __init__(self, rows: int = 1, cols: int = 254, layers: int = 1):
        self.rows = rows
        self.cols = cols
        self.layers = layers
        total = rows * cols * layers
        assert total == CAPACITY_CONTAINERS, (
            f"空间大小必须为254，当前={total}"
        )
        # 展平存储: [layer][row][col]
        self._containers: List[List[Container]] = []
        idx = 0
        for _ in range(layers):
            layer = []
            for _ in range(rows):
                row = []
                for _ in range(cols):
                    row.append(Container(index=idx))
                    idx += 1
                layer.append(row)
            self._containers.append(layer)

    def connect(self, container_index: int, observer: YinYang) -> None:
        """建立容器与观察者的统计连接（虚无→间接存在）"""
        layer, row, col = self._index_to_loc(container_index)
        c = self._containers[layer][row][col]
        c.is_observed = True
        if observer == YinYang.YIN:
            c.yin_connection = True
        else:
            c.yang_connection = True
        c.fill_count += 1

    def _index_to_loc(self, idx: int) -> Tuple[int, int, int]:
        layer = idx // (self.rows * self.cols)
        rem = idx % (self.rows * self.cols)
        row = rem // self.cols
        col = rem % self.cols
        return layer, row, col

    def observe_frequency(self) -> Tuple[int, int]:
        """观察频率 = 阴侧连接数 & 阳侧连接数"""
        yin = sum(
            1 for layer in self._containers
            for row in layer
            for c in row if c.yin_connection
        )
        yang = sum(
            1 for layer in self._containers
            for row in layer
            for c in row if c.yang_connection
        )
        return yin, yang

    def observed_total(self) -> int:
        """已观测容器总数"""
        return sum(
            1 for layer in self._containers
            for row in layer
            for c in row if c.is_observed
        )

    def estimated_total(self, rows_completed: int) -> int:
        """
        最省力估算总量

        总量 = 已完成行数 * 254 + 当前行已填充数
        不用逐个统计每个容器
        """
        layers_done = rows_completed // self.rows
        rows_in_layer = rows_completed % self.rows
        return (
            layers_done * self.rows * self.cols
            + rows_in_layer * self.cols
        )


class ObserverState:
    """观察者状态（阴+阳）"""
    def __init__(self):
        self.yin_filled: bool = False
        self.yang_filled: bool = False
        self.carry_count: int = 0  # 进位次数（统计行数）

    @property
    def full(self) -> bool:
        return self.yin_filled and self.yang_filled


class Full256System:
    """
    256 满态系统（阴+阳外部 + 254容器内部）

    数学：2（观察者） + 254（容器） = 256 = 2**8

    观察者（阴+阳）：
      - 不进位，统计者不是被统计者
      - 统计内部254个容器的填充频率
      - 自身进位 = 统计行数（每满254换一行）

    容器（254）：
      - 被观察者统计，互相隔离（间接存在）
      - 进位 = 换行（统计已填满多少行）
    """

    def __init__(self):
        self.observers = ObserverState()
        self.space = ContainerSpace254(rows=1, cols=254, layers=1)
        self.carry_rows: int = 0

    def fill(self, observer: YinYang, container_index: int) -> bool:
        """
        填充操作：观察者统计一个容器

        返回：是否触发了换行进位
        """
        self.space.connect(container_index, observer)
        total = self.space.observed_total()
        if total % CAPACITY_CONTAINERS == 0 and total > 0:
            self.carry_rows += 1
            self.observers.carry_count = self.carry_rows
            return True
        return False

    def indirect_density(self) -> float:
        """间接存在密度"""
        return self.space.observed_total() / CAPACITY_CONTAINERS

    def status(self) -> dict:
        yin, yang = self.space.observe_frequency()
        return {
            "容器": f"{self.space.observed_total()}/{CAPACITY_CONTAINERS}",
            "阴频率": yin,
            "阳频率": yang,
            "进位行数": self.carry_rows,
            "观察者满": self.observers.full,
            "满态256": self.carry_rows >= 1 and self.space.observed_total() >= CAPACITY_CONTAINERS,
        }


class TwoDimensionalSpace:
    """
    2D 空间进制（时间行 × 空间列）

    行 = 时间（不同时间片的统计行）
    列 = 空间（同一时间片内254个容器位置）
    进位 = 时间推进 = 统计频次
    """

    def __init__(self, max_rows: int = 10):
        self.max_rows = max_rows
        self.rows = [
            ContainerSpace254(rows=1, cols=254, layers=1)
            for _ in range(max_rows)
        ]
        self.current_row = 0

    def fill_next(self, observer: YinYang) -> bool:
        """填充下一个可用容器，返回是否触发换行进位"""
        space = self.rows[self.current_row]
        idx = space.observed_total() % CAPACITY_CONTAINERS
        space.connect(idx, observer)
        if space.observed_total() >= CAPACITY_CONTAINERS:
            self.current_row += 1
            return True
        return False

    def total_observed(self) -> int:
        return sum(s.observed_total() for s in self.rows[:self.current_row + 1])


class ThreeDimensionalSpace:
    """
    3D 空间进制（三层堆叠）

    Layer 0 = 阴侧容器（与阴观察者连接优先）
    Layer 1 = 混元容器（阴阳共同连接）
    Layer 2 = 阳侧容器（与阳观察者连接优先）
    """

    def __init__(self):
        # 3层，每层254个容器
        self.layers = [
            ContainerSpace254(rows=1, cols=254, layers=1),
            ContainerSpace254(rows=1, cols=254, layers=1),
            ContainerSpace254(rows=1, cols=254, layers=1),
        ]

    def connect_layer(self, layer: int, idx: int, obs: YinYang) -> None:
        self.layers[layer].connect(idx, obs)

    def yinyang_ratio(self) -> Tuple[float, float, float]:
        yin = self.layers[0].observed_total()
        mixed = self.layers[1].observed_total()
        yang = self.layers[2].observed_total()
        total = yin + mixed + yang
        if total == 0:
            return 0.33, 0.33, 0.33
        return yin / total, mixed / total, yang / total


class BinaryStatisticalSystem:
    """
    二进制统计系统主类

    整合：
      - 256满态（阴+阳外部 + 254容器内部）
      - 2D空间进制（时间行×空间列）
      - 3D空间进制（阴/混/阳三层）
      - 进位统计 & 间接存在密度
    """

    def __init__(self):
        self.full256 = Full256System()
        self.space2d = TwoDimensionalSpace(max_rows=10)
        self.space3d = ThreeDimensionalSpace()
        self.history: List[dict] = []

    def count(
        self,
        container_index: int,
        observer: YinYang,
        layer_3d: Optional[int] = None,
    ) -> dict:
        """执行一次统计计数"""
        carry = self.full256.fill(observer, container_index)
        self.space2d.fill_next(observer)
        if layer_3d is not None:
            self.space3d.connect_layer(layer_3d, container_index, observer)

        state = {
            "observer": observer.name,
            "container": container_index,
            "indirect_density": round(self.full256.indirect_density(), 4),
            "carry": carry,
            "total": self.full256.space.observed_total(),
        }
        self.history.append(state)
        return state

    def summary(self) -> dict:
        yin, yang = self.full256.space.observe_frequency()
        ratio = self.space3d.yinyang_ratio()
        return {
            "间接存在密度": f"{self.full256.indirect_density():.4f}",
            "容器已统计": f"{self.full256.space.observed_total()}/{CAPACITY_CONTAINERS}",
            "阴频率": yin,
            "阳频率": yang,
            "2D总已观测": self.space2d.total_observed(),
            "3D阴阳比例": f"阴={ratio[0]:.2f} 混={ratio[1]:.2f} 阳={ratio[2]:.2f}",
            "总计数次数": len(self.history),
        }


if __name__ == "__main__":
    import random
    random.seed(42)

    print("=" * 60)
    print("254 二进制统计系统演示")
    print("=" * 60)

    sys = BinaryStatisticalSystem()

    print("\n【填充过程】")
    for i in range(100):
        obs = YinYang.YIN if i % 2 == 0 else YinYang.YANG
        layer = i % 3
        state = sys.count(container_index=i % 254, observer=obs, layer_3d=layer)
        if i % 20 == 0:
            print(
                f"  #{i:3d} obs={obs.name} c={i % 254} "
                f"density={state['indirect_density']:.4f} carry={state['carry']}"
            )

    print("\n【最终状态】")
    for k, v in sys.summary().items():
        print(f"  {k}: {v}")
