"""
窄腰中间表示 (Narrow-Waist IR)
===============================
几何范畴论视角的统一中间表示。

核心设计原则：
1. 窄腰 = 不可再压缩的关系结构
2. 刚性包含：空间漏斗不是括号，是拓扑约束
3. 自举：编译器本身也用这段 IR 写成

17种IR节点类型，覆盖所有编程语言的语义。

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum, auto
from uuid import uuid4
import hashlib


class GeometricPrimitive(Enum):
    """几何原子：空间漏斗的最细粒度关系基底"""
    POINT = "⊙"       # 点（零维存在）
    LINE = "─"        # 线段（一维态射）
    PLANE = "▢"       # 平面（二维关系面）
    VOLUME = "⬡"      # 体（三维关系体）
    FIBER = "↕"       # 纤维（垂直截面）
    MORPHISM = "→"    # 态射（空间变换）
    CONTRAVARIANT = "↚"  # 反变态射
    EQUIVALENCE = "≅"  # 同伦等价


class IRNodeKind(Enum):
    """
    窄腰 IR 节点类型——宇宙中最精简的17种关系操作
    
    【存在性】
    - UNIT: 单元/身份（⊙ 零维点）
    - VOID: 空/未定义
    - WITNESS: 同伦见证
    
    【空间变换】
    - PROJECT: 投影（高维→低维，漏斗窄化）
    - INJECT: 注入（低维→高维）
    - LIFT: 提升（纤维丛截面选择）
    
    【关系构造】
    - PRODUCT: 卡氏积（关系并行AND）
    - COPRODUCT: 余积（关系选择OR）
    - EXPONENTIAL: 指数对象（关系函数空间→λ）
    - EQUALIZER: 等化子（共同满足约束）
    - COEQUALIZER: 余等化子（商掉等价关系）
    
    【时间与因果】
    - CAUSE: 因果发射
    - EFFECT: 效果接收
    - PARALLEL: 并行关系（不因果相连）
    
    【范畴编织】
    - BRAID: 编织（身份切换/认知切换）
    - TWIST: 扭转（视角反转）
    - COHERENCE: 协调性约束
    """
    # 存在性
    UNIT = auto()
    VOID = auto()
    WITNESS = auto()
    
    # 空间变换
    PROJECT = auto()
    INJECT = auto()
    LIFT = auto()
    
    # 关系构造
    PRODUCT = auto()
    COPRODUCT = auto()
    EXPONENTIAL = auto()
    EQUALIZER = auto()
    COEQUALIZER = auto()
    
    # 时间与因果
    CAUSE = auto()
    EFFECT = auto()
    PARALLEL = auto()
    
    # 范畴编织
    BRAID = auto()
    TWIST = auto()
    COHERENCE = auto()


@dataclass
class SpaceSlice:
    """空间切片：某一时刻的宇宙截面快照"""
    dimensions: int
    coordinates: Dict[str, float]
    embedding: Optional[str] = None

    def __hash__(self):
        coord_key = "|".join(f"{k}={v}" for k, v in sorted(self.coordinates.items()))
        return hash((self.dimensions, coord_key, self.embedding or ""))


@dataclass
class TimeSlice:
    """时间切片：关系网络的瞬时快照"""
    timestamp: float
    causal_frontier: Set[str]
    stable_nodes: Set[str]

    def overlaps(self, other: 'TimeSlice') -> bool:
        """两个时间切片是否有因果重叠"""
        return bool(self.causal_frontier & other.causal_frontier)


@dataclass
class MorphismType:
    """态射类型：关系变换的拓扑分类"""
    source_dimension: int
    target_dimension: int
    is_injective: bool
    is_surjective: bool
    is_bijective: bool

    def compose(self, other: 'MorphismType') -> 'MorphismType':
        """态射复合"""
        return MorphismType(
            source_dimension=other.source_dimension,
            target_dimension=self.target_dimension,
            is_injective=other.is_injective and self.is_injective,
            is_surjective=self.is_surjective and other.is_surjective,
            is_bijective=False
        )


@dataclass
class HomotopyClass:
    """
    同伦等价类：漏斗压缩的核心
    
    所有在几何空间中同伦等价的态射归为一类。
    这就是"漏斗大开口→小开口装瓶"的数学本质。
    """
    equivalence_id: str
    representative: str
    member_source_langs: Set[str]
    member_target_langs: Set[str]
    geometric_dimensions: Set[int]
    compression_ratio: float = 1.0

    def merge_with(self, other: 'HomotopyClass') -> 'HomotopyClass':
        """合并两个同伦类"""
        return HomotopyClass(
            equivalence_id=f"equiv_{hashlib.md5((self.equivalence_id + other.equivalence_id).encode()).hexdigest()[:8]}",
            representative=self.representative,
            member_source_langs=self.member_source_langs | other.member_source_langs,
            member_target_langs=self.member_target_langs | other.member_target_langs,
            geometric_dimensions=self.geometric_dimensions | other.geometric_dimensions,
            compression_ratio=(self.compression_ratio + other.compression_ratio) / 2
        )


@dataclass
class IRNode:
    """
    窄腰 IR 节点——几何范畴中的最小关系原子
    
    属性：
        kind: 节点类型（17种之一）
        node_id: 唯一标识
        label: 标签
        operands: 子节点列表
        meta: 元数据
        space_slice: 几何属性
        time_slice: 时间属性
        homotopy_class: 同伦等价类
        source_lang: 来源语言
        source_span: 源代码位置
    """
    kind: IRNodeKind
    node_id: str = field(default_factory=lambda: str(uuid4())[:8])
    label: str = ""
    operands: List['IRNode'] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    space_slice: Optional[SpaceSlice] = None
    time_slice: Optional[TimeSlice] = None
    homotopy_class: Optional[HomotopyClass] = None
    source_lang: str = ""
    source_span: str = ""

    def __repr__(self):
        return f"IR::{self.kind.name}[{self.label or self.node_id}]"

    def pretty(self, indent: int = 0) -> str:
        """树状打印"""
        prefix = "  " * indent
        lines = [f"{prefix}{self}"]
        for child in self.operands:
            lines.append(child.pretty(indent + 1))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "kind": self.kind.name,
            "node_id": self.node_id,
            "label": self.label,
            "operands": [op.to_dict() for op in self.operands],
            "meta": self.meta,
            "source_lang": self.source_lang,
            "source_span": self.source_span,
        }


class NarrowWaistIR:
    """
    窄腰中间表示构建器
    
    将任意语言的AST转换为统一的窄腰IR表示。
    """

    def __init__(self):
        self.nodes: List[IRNode] = []
        self.entry_point: Optional[IRNode] = None

    def emit(self, kind: IRNodeKind, label: str = "", **kwargs) -> IRNode:
        """发射一个IR节点"""
        node = IRNode(
            kind=kind,
            label=label,
            **kwargs
        )
        self.nodes.append(node)
        return node

    def unit(self, label: str = "") -> IRNode:
        """发射单元节点"""
        return self.emit(IRNodeKind.UNIT, label)

    def void(self, label: str = "") -> IRNode:
        """发射空节点"""
        return self.emit(IRNodeKind.VOID, label)

    def project(self, operand: IRNode, label: str = "") -> IRNode:
        """投影操作"""
        return self.emit(IRNodeKind.PROJECT, label, operands=[operand])

    def inject(self, operand: IRNode, label: str = "") -> IRNode:
        """注入操作"""
        return self.emit(IRNodeKind.INJECT, label, operands=[operand])

    def product(self, *operands: IRNode, label: str = "") -> IRNode:
        """卡氏积"""
        return self.emit(IRNodeKind.PRODUCT, label, operands=list(operands))

    def coproduct(self, *operands: IRNode, label: str = "") -> IRNode:
        """余积"""
        return self.emit(IRNodeKind.COPRODUCT, label, operands=list(operands))

    def lambda_(self, param: IRNode, body: IRNode, label: str = "") -> IRNode:
        """Lambda表达式（指数对象）"""
        return self.emit(IRNodeKind.EXPONENTIAL, label, operands=[param, body])

    def cause(self, effect: IRNode, label: str = "") -> IRNode:
        """因果发射"""
        return self.emit(IRNodeKind.CAUSE, label, operands=[effect])

    def braid(self, left: IRNode, right: IRNode, label: str = "") -> IRNode:
        """编织（身份切换）"""
        return self.emit(IRNodeKind.BRAID, label, operands=[left, right])

    def to_list(self) -> List[dict]:
        """转换为列表形式"""
        return [node.to_dict() for node in self.nodes]

    def __repr__(self):
        return f"<NarrowWaistIR nodes={len(self.nodes)} entry={self.entry_point}>"
