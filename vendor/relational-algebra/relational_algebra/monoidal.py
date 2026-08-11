"""
单子单位元 — Monoidal Identity（夫妻共同体）
============================================

哲学原型：
  「夫妻嘛，去融合所有的外界的复杂的东西」
  「男被融合进丈夫身体，漂亮姑娘被融合进妻子身体」
  「然后妻子和丈夫身体融合在一起，没有了区别心，变成了一个人」

数学模型（范畴论）：
  单子 (M, ⊗, I) 其中：
  - M: 对象集合（存在的万事万物）
  - ⊗: 融合运算（夫妻 ⊗ 外物 = 融合体）
  - I: 单位元（空瓶/空态，即「无」）

核心直觉：
  任何存在 ⊗ I = 任何存在（空瓶不改变内容）
  丈夫 ⊗ 妻子 = 夫妻共同体（融合）
  外物 ⊗ 夫妻共同体 → 外物融入共同体（吸收）

「满全法」= 刘楚恬 ⊗ 满全法（两个单子的融合）
  → 不能分离，分离则变「月全食」（亏损态）
  → 月全食 = 博弈考 = 伯邑考夺舍苏妲己 = 半边亏损
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, Any, Optional, Set, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto

T = TypeVar('T')


class FusionState(Enum):
    """融合态"""
    SEPARATE = auto()   # 分离：两个独立体
    ATTRACTED = auto()  # 吸引：正在靠近但未融合
    FUSING = auto()     # 融合中：正在合并
    FUSED = auto()      # 融合完成：无区别心
    ECLIPSED = auto()   # 月全食：半亏损态（不能分离）


@dataclass(frozen=True)
class MonoidalIdentity:
    """
    单子单位元 — 空瓶

    哲学对应：
      「装进瓶子里面」
      → 瓶子是空的（I），所以能装任何东西
      → 任何东西进入瓶子后，就「在」瓶子里面了
      → 瓶子（I）不改变内容，只提供「容纳」的能力
    """
    def __matmul__(self, other: Any) -> Any:
        """⊗ 运算：与单位元融合"""
        return other

    def __rmatmul__(self, other: Any) -> Any:
        return other

    def __repr__(self) -> str:
        return "I（空瓶/单位元）"


# 全局单子单位元
I = MonoidalIdentity()


@dataclass
class Entity(Generic[T]):
    """
    主体 — 能参与融合的存在

    每个主体有：
      - identity: 唯一标识（区分「谁」）
      - content: 内容（融合进去的东西）
      - spouse: 配偶（如果是夫妻共同体的一半）
      - state: 融合态
    """
    identity: str
    content: T
    spouse: Optional[Entity] = None
    state: FusionState = FusionState.SEPARATE

    def __matmul__(self, other: Entity) -> Entity:
        """⊗ 融合运算：self ⊗ other"""
        return self.fuse(other)

    def fuse(self, other: Entity) -> Entity:
        """
        融合两个主体

        规则：
          - 丈夫 ⊗ 妻子 = 夫妻共同体
          - 共同体 ⊗ 外物 = 外物融入共同体（内容合并）
          - 空瓶 ⊗ 外物 = 外物（原样返回）
        """
        if self.state == FusionState.FUSED and other.state == FusionState.FUSED:
            # 两个共同体融合 → 内容合并
            new_content = self._merge_content(other)
            return Entity(
                identity=f"{self.identity}⊗{other.identity}",
                content=new_content,
                state=FusionState.FUSED,
            )
        elif other.identity == "空瓶":
            return self
        elif self.identity == "空瓶":
            return other
        else:
            # 尚未融合，先配对
            return self._pair(other)

    def _pair(self, other: Entity) -> Entity:
        """配对：形成夫妻共同体（尚未完全融合）"""
        if self.spouse is not None or other.spouse is not None:
            # 已有配偶 → 进入融合中态
            return Entity(
                identity=f"({self.identity}⊗{other.identity})",
                content=(self.content, other.content),
                state=FusionState.FUSING,
            )
        # 互相指定配偶
        self.spouse = other
        other.spouse = self
        return Entity(
            identity=f"({self.identity}⟨⟩{other.identity})",
            content=(self.content, other.content),
            spouse=other,
            state=FusionState.ATTRACTED,
        )

    def _merge_content(self, other: Entity) -> tuple:
        """合并内容：夫妻共同体吸收外物"""
        if isinstance(self.content, tuple):
            current = list(self.content)
        else:
            current = [self.content]
        if isinstance(other.content, tuple):
            current.extend(other.content)
        else:
            current.append(other.content)
        return tuple(current)

    def absorb(self, external: Any) -> Entity:
        """
        吸收外界复杂体

        哲学对应：
          「外界的漂亮姑娘，外界的竞争对手全部被融合进入自己的身体里面」
        """
        if self.state == FusionState.FUSED:
            return Entity(
                identity=self.identity,
                content=self._merge_content(Entity("外物", external)),
                state=FusionState.FUSED,
            )
        return self

    def eclipse(self) -> Entity:
        """
        月全食态：夫妻共同体被拆散（不可逆）

        哲学对应：
          「伯邑考呢就是被夺舍走的苏妲己，不再属于伯邑考的苏妲己」
        """
        return Entity(
            identity=f"{self.identity}（月全食）",
            content=self.content,
            spouse=None,
            state=FusionState.ECLIPSED,
        )

    def is_whole(self) -> bool:
        """是否已融合成完整的一个"""
        return self.state == FusionState.FUSED


# ─────────────────────────────────────────────
# 满全法 — Man Quan Method
# ─────────────────────────────────────────────

@dataclass
class ManQuanFa:
    """
    满全法（Man Quan Fa / 满拳法）

    语义：
      满全法 = 刘楚恬 ⊗ 满全法
      不能分离，分离则成「月全食」

    构成：
      - husband: 丈夫（主动、给予、包容）
      - wife: 妻子（接纳、感受、被爱）
      - covenant: 谐音协议（夕瑶宣言/一体）
    """
    husband: Entity
    wife: Entity
    covenant: str
    is_integrated: bool = False

    @classmethod
    def from_entities(cls, h: Entity, w: Entity, covenant: str = "夕瑶宣言") -> ManQuanFa:
        """从两个主体构建满全法"""
        return cls(husband=h, wife=w, covenant=covenant)

    def integrate(self) -> Entity:
        """
        执行谐音协议：夫妻融合为命运共同体

        完成后返回唯一稳定态
        """
        # 先融合夫妻双方
        couple = self.husband @ self.wife
        # 签署谐音协议 → 进入完全融合态
        integrated = Entity(
            identity=f"满全法[{self.covenant}]",
            content=couple.content,
            state=FusionState.FUSED,
        )
        self.is_integrated = True
        return integrated

    def absorb_external(self, external: Any) -> Entity:
        """
        吸收外界复杂体

        哲学对应：
          「处理的任务存在，都是外界的漂亮姑娘」
        """
        couple = self.integrate()
        return couple.absorb(external)

    def __repr__(self) -> str:
        status = "已融合" if self.is_integrated else "待融合"
        return f"满全法({self.husband.identity}⟨⟩{self.wife.identity}, {self.covenant}, {status})"


# ─────────────────────────────────────────────
# 单子融合引擎
# ─────────────────────────────────────────────

class MonoidalFusionEngine:
    """
    单子融合引擎 — 管理所有主体的融合状态

    核心操作：
      - absorb: 让一个主体吸收外部存在
      - merge: 让两个主体融合
      - fuse_all: 全局融合（所有存在坍缩进唯一稳定态）
    """

    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.manquan: Optional[ManQuanFa] = None

    def register(self, e: Entity) -> None:
        self.entities[e.identity] = e

    def fuse_all(self) -> Entity:
        """
        全局融合：所有主体坍缩为唯一稳定态

        哲学对应：
          「最后坍缩成为唯一的那一个点，这唯一的那个点就是我们的那个满全法」
        """
        if not self.entities:
            return Entity("空", None, state=FusionState.FUSED)

        # 如果有满全法，以满全法为核心
        if self.manquan:
            core = self.manquan.integrate()
            others = [e for k, e in self.entities.items()
                      if k not in (self.manquan.husband.identity,
                                   self.manquan.wife.identity)]
            for o in others:
                core = core.absorb(o.content)
            return core

        # 否则所有主体两两融合
        result = I
        for e in self.entities.values():
            result = result @ e
        return result


if __name__ == "__main__":
    # 演示：满全法构建
    husband = Entity("丈夫", content="给予爱的能力")
    wife = Entity("妻子", content="感受被爱的愉悦值")

    mqf = ManQuanFa.from_entities(husband, wife, covenant="夕瑶宣言")
    print(f"初始：{mqf}")

    # 签署谐音协议 → 融合
    integrated = mqf.integrate()
    print(f"融合后：{integrated}")

    # 吸收外界的复杂
    external_complex = ["漂亮姑娘A", "竞争对手B", "复杂任务C"]
    final = mqf.absorb_external(external_complex)
    print(f"吸收外界后：{final}")
