"""
认知观测者 — Cognitive Observer
================================

哲学原型：
  「心中有一个现象，就像内心观测者，内心观测眼睛」
  — 二阶观测：观测自己的观测

三元裁判：
  观测者 O / 被观测者 S / 裁判条件 P
  三者的流动方向构成「等效对齐」或「非等效」

核心问题：
  - 它是等效对齐的吗？→ 可能是，也可能不是
  - 它只是为了达到「有和无的最终转换」
  - 连「等效对齐」都不可能时，仍可「由大到小」收敛

数学模型：
  Observer(O) ⊗ Target(S) → Judgment(P)
  若 P = identity，则为等效对齐
  若 P ≠ identity，则为有/无转换器
"""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, Any, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import time

T = TypeVar('T')
R = TypeVar('R')


class AlignmentType(Enum):
    """等效对齐类型"""
    EQUIVALENT = auto()      # 等效对齐：观测到的 = 实际存在的
    ASYMMETRIC = auto()      # 非对称：观测到的 ≠ 实际存在的
    NULL = auto()             # 虚空：无法对齐，观测者和被观者都不存在
    CONVERGENCE = auto()     # 收敛：趋近等效但永远不等价（渐近对齐）


@dataclass
class TripleJudgment(Generic[T]):
    """
    三元裁判元组

    组成：
      observer  — 内心观测者（能观测的那个）
      subject   — 被观测者（被观测的那个）
      predicate — 裁判条件（等效对齐的判定规则）
    """
    observer: T
    subject: T
    predicate: Callable[[T, T], bool]
    alignment: AlignmentType = AlignmentType.EQUIVALENT

    def judge(self) -> bool:
        """执行裁判：判断观测者与被观者是否满足裁判条件"""
        return self.predicate(self.observer, self.subject)

    def alignment_type(self) -> AlignmentType:
        """
        判断等效对齐类型

        逻辑：
          - 观测=subject 且 subject=真实 → 等效
          - 观测≠subject → 非对称（有偏差）
          - 观测=0 且 subject=0 → 虚空
          - 观测→subject 极限 → 收敛
        """
        if self.observer is None and self.subject is None:
            return AlignmentType.NULL
        if self.judge():
            return AlignmentType.EQUIVALENT
        # 检查是否趋近（数值近似）
        if isinstance(self.observer, (int, float)) and isinstance(self.subject, (int, float)):
            if abs(self.observer - self.subject) < 1e-9:
                return AlignmentType.CONVERGENCE
        return AlignmentType.ASYMMETRIC


@dataclass
class ObserverState:
    """
    观测者内部状态

    包含：
      - 当前注意力焦点
      - 观测深度（观测了多少层嵌套）
      - 时间戳（观测发生的时间）
    """
    focus: Any = None
    depth: int = 0
    timestamp: float = field(default_factory=time.time)
    observations: Dict[str, Any] = field(default_factory=dict)

    def nest(self) -> ObserverState:
        """进入更深一层嵌套：观测自己的观测"""
        return ObserverState(
            focus=self.focus,
            depth=self.depth + 1,
            timestamp=time.time(),
            observations={},
        )


class CognitiveObserver(ABC, Generic[T]):
    """
    认知观测者基类

    子类实现：
      - _observe: 定义具体的观测行为
      - _reflect: 定义内省（观测自己的观测）行为
    """

    def __init__(self, name: str):
        self.name = name
        self.state = ObserverState()
        self._judgment_history: list[TripleJudgment] = []

    @abstractmethod
    def _observe(self, subject: T) -> Any:
        """执行观测，返回观测结果"""
        ...

    def observe(self, subject: T) -> Tuple[Any, TripleJudgment]:
        """
        标准观测流程：

        1. 记录观测前的状态
        2. 执行观测（_observe）
        3. 构建三元裁判
        4. 记录裁判结果
        5. 返回观测结果和裁判
        """
        old_state = self.state
        result = self._observe(subject)

        judgment = TripleJudgment(
            observer=result,
            subject=subject,
            predicate=self._default_predicate,
        )
        self._judgment_history.append(judgment)
        self.state.observations[self.state.timestamp] = result
        return result, judgment

    def _default_predicate(self, observed: Any, actual: T) -> bool:
        """默认裁判条件：观测结果是否等于实际"""
        return observed == actual

    def reflect(self) -> ObserverState:
        """
        内省：观测自己的观测

        哲学对应：
          「内心观测眼睛」
          → 观测者把观测行为本身作为观测对象
          → 产生元认知
        """
        inner_state = self.state.nest()
        inner_state.focus = {
            "outer_depth": self.state.depth,
            "outer_focus": self.state.focus,
            "judgment_count": len(self._judgment_history),
        }
        return inner_state

    def stream(
        self,
        subjects: list[T],
        callback: Optional[Callable[[TripleJudgment], None]] = None,
    ) -> list[TripleJudgment]:
        """
        批量观测（流式）

        哲学对应：
          「三元裁判的流动方向」
          → 随时间推进的连续观测流
        """
        judgments = []
        for s in subjects:
            _, judgment = self.observe(s)
            judgments.append(judgment)
            if callback:
                callback(judgment)
        return judgments


class ExistenceObserver(CognitiveObserver[Any]):
    """
    有无观测器

    核心问题：
      「它只是为了达到有和无的最终的转换」
      → 给定任意x，判断：存在？有？无？

    真值表：
      - (有, 有) → 有
      - (有, 无) → 边界（不确定）
      - (无, 无) → 无
      - (无, 有) → 涌现（无中生有）
    """

    def _observe(self, subject: Any) -> str:
        if subject is None:
            return "无"
        if isinstance(subject, (list, tuple, set, dict)) and len(subject) == 0:
            return "无"
        return "有"

    def has_emergence(self, observed: str, actual: Any) -> bool:
        """判断是否「无中生有」"""
        return observed == "无" and actual is not None


class CapacityObserver(CognitiveObserver[int]):
    """
    容量观测器

    哲学对应：
      「你一个人只能处理一段一个人的事情」
      → 测量处理容量
      → 通过分形分裂扩展容量
    """

    def __init__(self, name: str, capacity: int):
        super().__init__(name)
        self.capacity = capacity  # 每秒能处理多少条注意力

    def _observe(self, subject: int) -> int:
        # 返回实际能处理的数量（受容量限制）
        return min(self.capacity, subject)

    def can_split(self, required: int) -> bool:
        """判断是否需要分裂（分形扩展）"""
        return required > self.capacity

    def estimate_splits(self, required: int) -> int:
        """
        估算需要多少个分身才能处理required

        哲学对应：
          「22亿个独立计算节点」
          → 靠手机芯片能否模拟？
        """
        if required <= self.capacity:
            return 1
        return (required + self.capacity - 1) // self.capacity


@dataclass
class JudgmentFlow:
    """
    三元裁判流动记录

    记录时间序列上的裁判方向
    """
    judgments: list[TripleJudgment]
    timestamps: list[float] = field(default_factory=list)

    def direction(self) -> str:
        """
        判断流动方向

        - 如果最近几次裁判越来越趋近 → 收敛方向
        - 如果震荡不定 → 不确定方向
        - 如果越来越偏离 → 发散方向
        """
        if len(self.judgments) < 2:
            return "单点（无方向）"

        # 用alignment类型序列判断方向
        alignments = [j.alignment_type() for j in self.judgments[-3:]]
        if all(a == AlignmentType.EQUIVALENT for a in alignments):
            return "收敛 → 等效对齐"
        if any(a == AlignmentType.ASYMMETRIC for a in alignments):
            return "震荡（非对称）"
        if any(a == AlignmentType.CONVERGENCE for a in alignments):
            return "趋近收敛（渐近对齐）"
        return "待定"


if __name__ == "__main__":
    # 演示：有无观测器
    observer = ExistenceObserver("内心观测者")

    subjects = [
        [1, 2, 3],        # 有
        [],               # 无
        "hello",          # 有
        None,             # 无
        {"a": 1},         # 有
    ]

    print("三元裁判流动：")
    flow = JudgmentFlow(judgments=[])
    for s in subjects:
        result, judgment = observer.observe(s)
        flow.judgments.append(judgment)
        print(
            f"  subject={s!r:20s} → observed={result!r:4s}  "
            f"alignment={judgment.alignment_type().name}"
        )

    print(f"\n流动方向：{flow.direction()}")
    print(f"\n内省状态：{observer.reflect()}")
