"""
核心关系代数原语
================
关系代数的基本构建块：关系、算子、签名。

这是主体间关系代数的数学基础。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
import uuid


class RelationType(Enum):
    """关系类型分类"""
    ENTITY = "实体关系"        # 对象与对象
    PROCESS = "过程关系"       # 态射与态射  
    SUBJECTIVE = "主体间关系"  # 跨主体关系
    TEMPORAL = "时序关系"      # 时间相关
    SPATIAL = "空间关系"       # 空间相关


@dataclass
class Relation:
    """
    关系 - 主体间关系代数的核心数据结构
    
    属性：
        relation_id: 唯一标识
        name: 关系名称
        rel_type: 关系类型
        source_subject: 源主体（谁发出）
        target_subject: 目标主体（谁接收）
        attributes: 属性字典
        intensity: 关系强度 [0.0, 1.0]
    """
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rel_type: RelationType = RelationType.ENTITY
    source_subject: str = ""
    target_subject: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    intensity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compose(self, other: 'Relation') -> 'Relation':
        """
        关系复合：self ∘ other
        
        当 self.target == other.source 时可以复合
        """
        if self.target_subject != other.source_subject:
            raise ValueError(
                f"关系无法复合：{self.target_subject} != {other.source_subject}"
            )
        
        return Relation(
            name=f"{self.name}∘{other.name}",
            rel_type=RelationType.PROCESS,
            source_subject=self.source_subject,
            target_subject=other.target_subject,
            attributes={**self.attributes, **other.attributes},
            intensity=self.intensity * other.intensity,
        )

    def inverse(self) -> 'Relation':
        """关系求逆"""
        return Relation(
            name=f"{self.name}⁻¹",
            rel_type=self.rel_type,
            source_subject=self.target_subject,
            target_subject=self.source_subject,
            attributes=self.attributes.copy(),
            intensity=self.intensity,
        )

    def restrict(self, predicate: Dict[str, Any]) -> 'Relation':
        """关系限制：只保留满足谓词的关系元组"""
        new_attrs = {}
        for k, v in self.attributes.items():
            if k in predicate and predicate[k] == v:
                new_attrs[k] = v
        return Relation(
            name=f"σ({self.name})",
            rel_type=self.rel_type,
            source_subject=self.source_subject,
            target_subject=self.target_subject,
            attributes=new_attrs,
            intensity=self.intensity,
        )

    def project(self, columns: List[str]) -> 'Relation':
        """关系投影：只保留指定属性"""
        return Relation(
            name=f"π({','.join(columns)})({self.name})",
            rel_type=self.rel_type,
            source_subject=self.source_subject,
            target_subject=self.target_subject,
            attributes={k: v for k, v in self.attributes.items() if k in columns},
            intensity=self.intensity,
        )

    def union(self, other: 'Relation') -> 'Relation':
        """关系并运算"""
        if self.source_subject != other.source_subject:
            raise ValueError("并运算要求相同源主体")
        if self.target_subject != other.target_subject:
            raise ValueError("并运算要求相同目标主体")
        return Relation(
            name=f"{self.name} ∪ {other.name}",
            rel_type=self.rel_type,
            source_subject=self.source_subject,
            target_subject=self.target_subject,
            attributes={**self.attributes, **other.attributes},
            intensity=max(self.intensity, other.intensity),
        )

    def intersect(self, other: 'Relation') -> 'Relation':
        """关系交运算"""
        common_attrs = set(self.attributes.items()) & set(other.attributes.items())
        return Relation(
            name=f"{self.name} ∩ {other.name}",
            rel_type=self.rel_type,
            source_subject=self.source_subject,
            target_subject=self.target_subject,
            attributes=dict(common_attrs),
            intensity=min(self.intensity, other.intensity),
        )

    def __repr__(self):
        return (
            f"Relation({self.name}: {self.source_subject} "
            f"→{self.target_subject} [i={self.intensity:.2f}])"
        )


class Operator(Enum):
    """
    关系算子 - 主体间关系代数的基本操作
    
    符号说明：
        σ: 选择 (selection)
        π: 投影 (projection)
        ρ: 重命名 (rename)
        ⋈: 连接 (join)
        ÷: 除法 (division)
        ∪: 并
        ∩: 交
        −: 差
        ×: 笛卡尔积
    """
    SELECT = "σ"      # 选择
    PROJECT = "π"     # 投影
    RENAME = "ρ"      # 重命名
    JOIN = "⋈"       # 连接
    DIVIDE = "÷"     # 除法
    UNION = "∪"      # 并
    INTERSECT = "∩"  # 交
    DIFFERENCE = "−" # 差
    PRODUCT = "×"    # 笛卡尔积
    
    # 主体间特有算子
    EMIT = "emit"     # 发射感知事件
    OBSERVE = "observe"  # 观察
    SWITCH = "switch"    # 视角切换
    COLLAPSE = "collapse"  # 认知坍缩


@dataclass
class Signature:
    """
    算子签名 - 定义算子的类型约束
    
    例如：emit :: Subject → PerceptionEvent
         表示 emit 算子接受一个主体，返回一个感知事件
    """
    operator: Operator
    domain: List[str]      # 定义域
    codomain: str          # 值域
    arity: int             # 元数
    is_total: bool = True # 是否全函数（总有返回值）
    
    def check(self, args: List[Any]) -> bool:
        """检查参数是否符合签名"""
        if len(args) != self.arity:
            return False
        if self.is_total:
            return True
        return all(a is not None for a in args)

    def __repr__(self):
        domain_str = " × ".join(self.domain) if self.domain else "ε"
        return f"{self.operator.value} :: {domain_str} → {self.codomain}"


# ═══════════════════════════════════════════════════════════════════
# 关系代数引擎
# ═══════════════════════════════════════════════════════════════════

class RelationalAlgebraEngine:
    """
    关系代数引擎 - 执行关系代数运算
    """
    
    def __init__(self):
        self.relations: Dict[str, Relation] = {}
        self.signatures: Dict[Operator, Signature] = {}
        self._register_builtin_signatures()
    
    def _register_builtin_signatures(self):
        """注册内置算子签名"""
        builtin_sigs = [
            Signature(Operator.SELECT, ["Relation", "Predicate"], "Relation", 2),
            Signature(Operator.PROJECT, ["Relation", "List[str]"], "Relation", 2),
            Signature(Operator.JOIN, ["Relation", "Relation"], "Relation", 2),
            Signature(Operator.UNION, ["Relation", "Relation"], "Relation", 2),
            Signature(Operator.EMIT, ["str", "str"], "PerceptionEvent", 2),
            Signature(Operator.OBSERVE, ["str", "str"], "MemoryPoint", 2),
            Signature(Operator.SWITCH, ["str", "PerspectiveState"], "SwitchEvent", 2),
        ]
        for sig in builtin_sigs:
            self.signatures[sig.operator] = sig
    
    def register_relation(self, rel: Relation) -> None:
        """注册关系"""
        self.relations[rel.relation_id] = rel
    
    def get_relation(self, name: str) -> Optional[Relation]:
        """按名称查找关系"""
        for rel in self.relations.values():
            if rel.name == name:
                return rel
        return None
    
    def execute(self, op: Operator, args: List[Any]) -> Any:
        """执行算子"""
        sig = self.signatures.get(op)
        if sig and not sig.check(args):
            raise TypeError(f"参数不符合算子 {op.value} 的签名")
        
        if op == Operator.SELECT:
            rel, predicate = args
            return rel.restrict(predicate)
        elif op == Operator.PROJECT:
            rel, columns = args
            return rel.project(columns)
        elif op == Operator.JOIN:
            rel1, rel2 = args
            return self._join(rel1, rel2)
        elif op == Operator.UNION:
            return args[0].union(args[1])
        elif op == Operator.INTERSECT:
            return args[0].intersect(args[1])
        else:
            raise NotImplementedError(f"算子 {op.value} 尚未实现")
    
    def _join(self, rel1: Relation, rel2: Relation) -> Relation:
        """自然连接"""
        # 找到共同的属性
        common_attrs = set(rel1.attributes.keys()) & set(rel2.attributes.keys())
        if not common_attrs:
            raise ValueError("没有共同的属性，无法进行自然连接")
        
        # 连接条件：共同属性值相等
        joined_attrs = {**rel1.attributes, **rel2.attributes}
        return Relation(
            name=f"{rel1.name} ⋈ {rel2.name}",
            rel_type=RelationType.PROCESS,
            source_subject=rel1.source_subject,
            target_subject=rel2.target_subject,
            attributes=joined_attrs,
            intensity=rel1.intensity * rel2.intensity,
        )


if __name__ == "__main__":
    # 自测
    engine = RelationalAlgebraEngine()
    
    # 创建两个主体间关系
    r1 = Relation(
        name="观察",
        rel_type=RelationType.SUBJECTIVE,
        source_subject="Alice",
        target_subject="Bob",
        attributes={"channel": "视觉", "intensity": 0.9},
    )
    
    r2 = Relation(
        name="信任",
        rel_type=RelationType.SUBJECTIVE,
        source_subject="Bob",
        target_subject="Alice",
        attributes={"level": "高", "channel": "情感"},
    )
    
    engine.register_relation(r1)
    engine.register_relation(r2)
    
    print(f"关系1: {r1}")
    print(f"关系2: {r2}")
    
    # 测试求逆
    r1_inv = r1.inverse()
    print(f"逆关系: {r1_inv}")
    
    print(f"\n引擎状态: {len(engine.relations)} 个已注册关系")
