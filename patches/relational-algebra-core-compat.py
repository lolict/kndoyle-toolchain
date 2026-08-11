# compat 补丁：为 relational_algebra.core 补上 __init__.py 引用但缺失的顶层符号
# 背景: 源仓库 __init__.py 导入 core.selection/projection/natural_join/union/difference/SemiJoin,
#       但 core.py 只有 Relation 类方法, 无这些顶层定义 (上游版本不一致)
# 应用方式: 见 patches/README.md
from .core import Relation, RelationType


def selection(rel, predicate):
    return rel.restrict(predicate)


def projection(rel, columns):
    return rel.project(columns)


def natural_join(rel1, rel2):
    common = set(rel1.attributes) & set(rel2.attributes)
    joined = {**rel1.attributes, **rel2.attributes}
    return Relation(
        name=f"{rel1.name} ⋈ {rel2.name}",
        rel_type=RelationType.PROCESS,
        source_subject=rel1.source_subject,
        target_subject=rel2.target_subject,
        attributes=joined,
        intensity=rel1.intensity * rel2.intensity,
        metadata={"common_attrs": sorted(common)},
    )


def union(rel1, rel2):
    return rel1.union(rel2)


def difference(rel1, rel2):
    attrs = {k: v for k, v in rel1.attributes.items()
             if (k, v) not in set(rel2.attributes.items())}
    return Relation(
        name=f"{rel1.name} − {rel2.name}",
        rel_type=rel1.rel_type,
        source_subject=rel1.source_subject,
        target_subject=rel1.target_subject,
        attributes=attrs,
        intensity=rel1.intensity,
    )


class SemiJoin(Relation):
    """半连接: 只保留与右关系共同属性相关的关系"""
    def __init__(self, rel1, rel2, **kwargs):
        common = set(rel1.attributes) & set(rel2.attributes)
        filtered = {k: v for k, v in rel1.attributes.items()
                    if k in common and v == rel2.attributes.get(k)}
        super().__init__(
            name=f"{rel1.name} ⋉ {rel2.name}",
            rel_type=rel1.rel_type,
            source_subject=rel1.source_subject,
            target_subject=rel1.target_subject,
            attributes=filtered,
            intensity=rel1.intensity,
        )
