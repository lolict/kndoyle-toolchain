"""
认知相位分析器
==============
将主体认知映射为8维向量空间，用于分析和比较认知状态。

8维相位向量：
1. 创造维度 (CREATION)
2. 分析维度 (ANALYSIS)  
3. 感知维度 (PERCEPTION)
4. 情感维度 (EMOTION)
5. 社交维度 (SOCIAL)
6. 逻辑维度 (LOGIC)
7. 记忆维度 (MEMORY)
8. 反思维度 (REFLECTION)

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import math


class PhaseDimension(Enum):
    """相位维度枚举"""
    CREATION = "创造"
    ANALYSIS = "分析"
    PERCEPTION = "感知"
    EMOTION = "情感"
    SOCIAL = "社交"
    LOGIC = "逻辑"
    MEMORY = "记忆"
    REFLECTION = "反思"


@dataclass
class PhaseVector:
    """
    相位向量 - 8维认知状态向量
    
    每个维度取值范围 [0.0, 1.0]，表示在该维度上的"认知投入度"。
    
    示例：
        vector = PhaseVector(
            creation=0.8,
            analysis=0.6,
            perception=0.9,
            emotion=0.7,
            social=0.3,
            logic=0.5,
            memory=0.6,
            reflection=0.4
        )
    """
    creation: float = 0.0
    analysis: float = 0.0
    perception: float = 0.0
    emotion: float = 0.0
    social: float = 0.0
    logic: float = 0.0
    memory: float = 0.0
    reflection: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "创造": self.creation,
            "分析": self.analysis,
            "感知": self.perception,
            "情感": self.emotion,
            "社交": self.social,
            "逻辑": self.logic,
            "记忆": self.memory,
            "反思": self.reflection,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'PhaseVector':
        """从字典创建"""
        return cls(
            creation=data.get("创造", 0.0),
            analysis=data.get("分析", 0.0),
            perception=data.get("感知", 0.0),
            emotion=data.get("情感", 0.0),
            social=data.get("社交", 0.0),
            logic=data.get("逻辑", 0.0),
            memory=data.get("记忆", 0.0),
            reflection=data.get("反思", 0.0),
        )

    def magnitude(self) -> float:
        """向量模长"""
        return math.sqrt(
            self.creation ** 2 +
            self.analysis ** 2 +
            self.perception ** 2 +
            self.emotion ** 2 +
            self.social ** 2 +
            self.logic ** 2 +
            self.memory ** 2 +
            self.reflection ** 2
        )

    def cosine_similarity(self, other: 'PhaseVector') -> float:
        """余弦相似度"""
        dot_product = (
            self.creation * other.creation +
            self.analysis * other.analysis +
            self.perception * other.perception +
            self.emotion * other.emotion +
            self.social * other.social +
            self.logic * other.logic +
            self.memory * other.memory +
            self.reflection * other.reflection
        )
        return dot_product / (self.magnitude() * other.magnitude() + 1e-10)

    def distance_to(self, other: 'PhaseVector') -> float:
        """欧氏距离"""
        return math.sqrt(
            (self.creation - other.creation) ** 2 +
            (self.analysis - other.analysis) ** 2 +
            (self.perception - other.perception) ** 2 +
            (self.emotion - other.emotion) ** 2 +
            (self.social - other.social) ** 2 +
            (self.logic - other.logic) ** 2 +
            (self.memory - other.memory) ** 2 +
            (self.reflection - other.reflection) ** 2
        )

    def dominant_dimension(self) -> PhaseDimension:
        """主导维度"""
        dims = [
            (PhaseDimension.CREATION, self.creation),
            (PhaseDimension.ANALYSIS, self.analysis),
            (PhaseDimension.PERCEPTION, self.perception),
            (PhaseDimension.EMOTION, self.emotion),
            (PhaseDimension.SOCIAL, self.social),
            (PhaseDimension.LOGIC, self.logic),
            (PhaseDimension.MEMORY, self.memory),
            (PhaseDimension.REFLECTION, self.reflection),
        ]
        return max(dims, key=lambda x: x[1])[0]

    @classmethod
    def default_creative(cls) -> 'PhaseVector':
        """默认创作相位"""
        return cls(creation=0.8, analysis=0.5, perception=0.6, emotion=0.7)

    @classmethod
    def default_analytical(cls) -> 'PhaseVector':
        """默认分析相位"""
        return cls(creation=0.3, analysis=0.9, perception=0.4, emotion=0.2, logic=0.9)

    @classmethod
    def default_balanced(cls) -> 'PhaseVector':
        """默认平衡相位"""
        return cls(creation=0.5, analysis=0.5, perception=0.5, emotion=0.5, 
                   social=0.5, logic=0.5, memory=0.5, reflection=0.5)


class CognitivePhaseAnalyzer:
    """
    认知相位分析器
    
    功能：
    1. 从上下文提取相位向量
    2. 计算相位相似度/距离
    3. 分析认知冲突
    4. 生成最优认知组合
    """

    def __init__(self):
        self.phase_history: List[PhaseVector] = []
        self.context_vectors: Dict[str, PhaseVector] = {}

    def analyze_text(self, text: str) -> PhaseVector:
        """
        从文本内容分析相位向量
        
        使用关键词匹配规则：
        - 创造类词汇 → 创造维度
        - 分析类词汇 → 分析维度
        - 等等
        """
        vector = PhaseVector()
        
        # 创造维度关键词
        creation_keywords = ["创造", "创新", "发明", "设计", "生成", "创作", "构思", "设想"]
        for kw in creation_keywords:
            if kw in text:
                vector.creation = min(1.0, vector.creation + 0.15)
        
        # 分析维度关键词
        analysis_keywords = ["分析", "研究", "探讨", "考察", "评估", "诊断", "检验"]
        for kw in analysis_keywords:
            if kw in text:
                vector.analysis = min(1.0, vector.analysis + 0.15)
        
        # 感知维度关键词
        perception_keywords = ["看到", "听到", "感知", "观察", "感觉", "发现"]
        for kw in perception_keywords:
            if kw in text:
                vector.perception = min(1.0, vector.perception + 0.15)
        
        # 情感维度关键词
        emotion_keywords = ["喜欢", "爱", "高兴", "悲伤", "愤怒", "恐惧", "希望", "担心"]
        for kw in emotion_keywords:
            if kw in text:
                vector.emotion = min(1.0, vector.emotion + 0.15)
        
        # 逻辑维度关键词
        logic_keywords = ["因为", "所以", "如果", "那么", "推理", "论证", "结论", "因此"]
        for kw in logic_keywords:
            if kw in text:
                vector.logic = min(1.0, vector.logic + 0.15)
        
        # 记忆维度关键词
        memory_keywords = ["记得", "回忆", "想起", "过去", "曾经", "经验", "历史"]
        for kw in memory_keywords:
            if kw in text:
                vector.memory = min(1.0, vector.memory + 0.15)
        
        # 反思维度关键词
        reflection_keywords = ["思考", "反思", "审视", "考虑", "琢磨", "揣摩", "悟"]
        for kw in reflection_keywords:
            if kw in text:
                vector.reflection = min(1.0, vector.reflection + 0.15)
        
        self.phase_history.append(vector)
        return vector

    def compare_phases(
        self, 
        phase1: PhaseVector, 
        phase2: PhaseVector
    ) -> Dict[str, Any]:
        """
        比较两个相位向量
        
        返回相似度、距离、冲突点等分析结果
        """
        cosine = phase1.cosine_similarity(phase2)
        distance = phase1.distance_to(phase2)
        
        # 找出冲突维度（差异 > 0.5）
        conflicts = []
        dims = [
            ("创造", phase1.creation, phase2.creation),
            ("分析", phase1.analysis, phase2.analysis),
            ("感知", phase1.perception, phase2.perception),
            ("情感", phase1.emotion, phase2.emotion),
            ("社交", phase1.social, phase2.social),
            ("逻辑", phase1.logic, phase2.logic),
            ("记忆", phase1.memory, phase2.memory),
            ("反思", phase1.reflection, phase2.reflection),
        ]
        for name, v1, v2 in dims:
            if abs(v1 - v2) > 0.5:
                conflicts.append({
                    "dimension": name,
                    "phase1_value": v1,
                    "phase2_value": v2,
                    "difference": abs(v1 - v2)
                })
        
        return {
            "cosine_similarity": cosine,
            "euclidean_distance": distance,
            "dominant_phase1": phase1.dominant_dimension().value,
            "dominant_phase2": phase2.dominant_dimension().value,
            "conflicts": conflicts,
            "is_compatible": len(conflicts) < 3,
        }

    def find_optimal_blend(
        self, 
        phases: List[PhaseVector],
        weights: List[float] = None
    ) -> PhaseVector:
        """
        找到多个相位的最优加权平均
        
        用于组合不同视角的认知优势
        """
        if not phases:
            return PhaseVector()
        
        if weights is None:
            weights = [1.0 / len(phases)] * len(phases)
        
        if len(weights) != len(phases):
            raise ValueError("权重数量必须与相位数量相同")
        
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        blended = PhaseVector(
            creation=sum(p.creation * w for p, w in zip(phases, weights)),
            analysis=sum(p.analysis * w for p, w in zip(phases, weights)),
            perception=sum(p.perception * w for p, w in zip(phases, weights)),
            emotion=sum(p.emotion * w for p, w in zip(phases, weights)),
            social=sum(p.social * w for p, w in zip(phases, weights)),
            logic=sum(p.logic * w for p, w in zip(phases, weights)),
            memory=sum(p.memory * w for p, w in zip(phases, weights)),
            reflection=sum(p.reflection * w for p, w in zip(phases, weights)),
        )
        
        return blended

    def generate_phase_report(self, vector: PhaseVector) -> str:
        """生成相位分析报告"""
        dominant = vector.dominant_dimension()
        report_lines = [
            "=" * 40,
            "认知相位分析报告",
            "=" * 40,
            f"主导维度: {dominant.value}",
            f"向量模长: {vector.magnitude():.3f}",
            "",
            "各维度得分:",
        ]
        
        dims = vector.to_dict()
        for name, value in dims.items():
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            report_lines.append(f"  {name}: [{bar}] {value:.2f}")
        
        report_lines.append("=" * 40)
        return "\n".join(report_lines)
