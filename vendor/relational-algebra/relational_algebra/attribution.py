"""
归属确定性引擎 (Attribution Engine)
====================================
确定"谁创造了什么"——用户、Agent还是平台。

三权分立原则：
- User: 用户原创贡献
- Agent: AI代为生成
- Platform: 平台自动功能

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from datetime import datetime


class AttributionSource(Enum):
    """归属来源枚举"""
    USER = "user"           # 用户原创
    AGENT = "agent"         # Agent生成
    PLATFORM = "platform"   # 平台功能
    COLLABORATION = "collab"  # 协作生成
    UNKNOWN = "unknown"      # 未知


class AttributionLevel(Enum):
    """归属确定性级别"""
    CERTAIN = "certain"     # 确定
    PROBABLE = "probable"   # 可能
    POSSIBLE = "possible"   # 也许
    UNLIKELY = "unlikely"   # 不太可能


@dataclass
class AttributionTag:
    """
    归属标签 - 单个创作片段的归属信息
    
    属性：
        tag_id: 标签唯一ID
        source: 归属来源
        level: 确定性级别
        confidence: 置信度 [0.0, 1.0]
        evidence: 证据列表
        contributor: 贡献者标识
        timestamp: 时间戳
        description: 描述
    """
    tag_id: str
    source: AttributionSource
    level: AttributionLevel
    confidence: float
    evidence: List[str] = field(default_factory=list)
    contributor: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""

    def is_user_owned(self) -> bool:
        """是否属于用户原创"""
        return self.source == AttributionSource.USER or (
            self.source == AttributionSource.COLLABORATION and self.confidence > 0.7
        )


@dataclass
class AttributionResult:
    """
    归属分析结果
    
    属性：
        result_id: 结果ID
        overall_source: 总体归属
        overall_confidence: 总体置信度
        tags: 各个片段的归属标签
        summary: 摘要说明
        breakdown: 归属分解（user/agent/platform百分比）
    """
    result_id: str
    overall_source: AttributionSource
    overall_confidence: float
    tags: List[AttributionTag] = field(default_factory=list)
    summary: str = ""
    breakdown: Dict[str, float] = field(default_factory=dict)

    def user_contribution_ratio(self) -> float:
        """用户贡献占比"""
        return self.breakdown.get("user", 0.0)

    def is_primarily_user(self) -> bool:
        """是否主要是用户原创"""
        return self.overall_source == AttributionSource.USER and self.overall_confidence > 0.6

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "result_id": self.result_id,
            "overall_source": self.overall_source.value,
            "overall_confidence": self.overall_confidence,
            "summary": self.summary,
            "breakdown": self.breakdown,
            "tags": [
                {
                    "tag_id": t.tag_id,
                    "source": t.source.value,
                    "confidence": t.confidence,
                    "description": t.description,
                }
                for t in self.tags
            ],
        }


class AttributionEngine:
    """
    归属确定性引擎
    
    分析创作内容的来源，确定是用户原创还是AI生成。
    
    分析维度：
    1. 词汇特征 - 复杂度、专业术语
    2. 句式结构 - 变化度、从句嵌套
    3. 创意程度 - 重复度、常规表达
    4. 上下文 - 对话历史中的角色
    5. 显式声明 - 用户明确说"帮我写"
    """

    # 用户词汇特征
    USER_PATTERNS = {
        "personal_pronouns": ["我", "我的", "咱们"],
        "informal": ["哈", "嘿", "哇", "啦"],
        "specific_knowledge": [],  # 用户专业领域
    }

    # Agent词汇特征
    AGENT_PATTERNS = {
        "formal": ["因此", "综上所述", "根据", "首先", "其次"],
        "structure_markers": ["第一", "第二", "第三", "一方面", "另一方面"],
        "hedging": ["可能", "也许", "或许", "通常"],
    }

    def __init__(self):
        self.analysis_history: List[AttributionResult] = []

    def analyze(
        self,
        content: str,
        context: Dict[str, Any] = None,
        user_id: str = "default_user"
    ) -> AttributionResult:
        """
        分析内容的归属
        
        参数：
            content: 待分析内容
            context: 上下文信息
            user_id: 用户标识
        
        返回：
            AttributionResult 分析结果
        """
        context = context or {}
        
        # 提取特征
        features = self._extract_features(content)
        
        # 计算各来源得分
        scores = self._compute_scores(features, context)
        
        # 确定归属
        overall_source = max(scores, key=scores.get)
        overall_confidence = scores[overall_source]
        
        # 生成标签
        tags = self._generate_tags(content, features, scores)
        
        # 计算分解
        breakdown = self._compute_breakdown(scores)
        
        result = AttributionResult(
            result_id=f"attr_{datetime.now().timestamp()}",
            overall_source=AttributionSource(overall_source),
            overall_confidence=overall_confidence,
            tags=tags,
            summary=self._generate_summary(scores, breakdown),
            breakdown=breakdown,
        )
        
        self.analysis_history.append(result)
        return result

    def _extract_features(self, content: str) -> Dict[str, Any]:
        """提取内容特征"""
        features = {
            "length": len(content),
            "word_count": len(content.split()),
            "has_personal_pronouns": any(p in content for p in self.USER_PATTERNS["personal_pronouns"]),
            "has_informal": any(p in content for p in self.USER_PATTERNS["informal"]),
            "has_formal_markers": any(p in content for p in self.AGENT_PATTERNS["formal"]),
            "has_structure_markers": any(p in content for p in self.AGENT_PATTERNS["structure_markers"]),
            "has_hedging": any(p in content for p in self.AGENT_PATTERNS["hedging"]),
            "sentence_count": content.count("。") + content.count("!") + content.count("?"),
            "avg_sentence_length": 0,
        }
        
        if features["sentence_count"] > 0:
            features["avg_sentence_length"] = features["word_count"] / features["sentence_count"]
        
        return features

    def _compute_scores(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """计算各来源得分"""
        scores = {
            "user": 0.0,
            "agent": 0.0,
            "platform": 0.0,
            "collab": 0.0,
        }
        
        # 用户特征
        if features["has_personal_pronouns"]:
            scores["user"] += 0.3
        if features["has_informal"]:
            scores["user"] += 0.2
        
        # Agent特征
        if features["has_formal_markers"]:
            scores["agent"] += 0.25
        if features["has_structure_markers"]:
            scores["agent"] += 0.25
        if features["has_hedging"]:
            scores["agent"] += 0.2
        
        # 长度因素
        if features["length"] > 500:
            scores["agent"] += 0.1
        
        # 上下文因素
        if context.get("is_generation_request"):
            scores["agent"] += 0.3
        if context.get("is_original_idea"):
            scores["user"] += 0.3
        
        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        # 协作得分
        scores["collab"] = min(0.5, scores["user"] * scores["agent"] * 4)
        
        return scores

    def _generate_tags(
        self,
        content: str,
        features: Dict[str, Any],
        scores: Dict[str, float]
    ) -> List[AttributionTag]:
        """生成归属标签"""
        tags = []
        
        # 主标签
        main_source = max(scores, key=scores.get)
        main_confidence = scores[main_source]
        
        level = AttributionLevel.CERTAIN if main_confidence > 0.7 else (
            AttributionLevel.PROBABLE if main_confidence > 0.5 else AttributionLevel.POSSIBLE
        )
        
        tags.append(AttributionTag(
            tag_id="main",
            source=AttributionSource(main_source),
            level=level,
            confidence=main_confidence,
            description=f"主要内容归属 ({main_source}: {main_confidence:.2f})"
        ))
        
        return tags

    def _compute_breakdown(self, scores: Dict[str, float]) -> Dict[str, float]:
        """计算归属分解"""
        return {
            "user": scores.get("user", 0.0),
            "agent": scores.get("agent", 0.0),
            "platform": scores.get("platform", 0.0),
        }

    def _generate_summary(self, scores: Dict[str, float], breakdown: Dict[str, float]) -> str:
        """生成摘要说明"""
        user_pct = int(breakdown.get("user", 0) * 100)
        agent_pct = int(breakdown.get("agent", 0) * 100)
        
        if user_pct > 70:
            return f"主要是用户原创内容（用户约{user_pct}%）"
        elif agent_pct > 70:
            return f"主要是AI生成内容（AI约{agent_pct}%）"
        elif user_pct > 40 and agent_pct > 40:
            return f"用户与AI协作生成（用户约{user_pct}%，AI约{agent_pct}%）"
        else:
            return "归属不确定"


class AttributionReport:
    """
    归属确定性分析报告
    
    用于生成详细的归属分析报告
    """

    def __init__(self, results: List[AttributionResult]):
        self.results = results

    def summary(self) -> Dict[str, Any]:
        """生成汇总统计"""
        if not self.results:
            return {"total_items": 0}
        
        total_user = sum(r.user_contribution_ratio() for r in self.results) / len(self.results)
        
        return {
            "total_items": len(self.results),
            "avg_user_contribution": total_user,
            "primarily_user_items": sum(1 for r in self.results if r.is_primarily_user()),
            "generation_time": datetime.now().isoformat(),
        }

    def to_json(self) -> str:
        """输出为JSON格式"""
        import json
        return json.dumps({
            "summary": self.summary(),
            "results": [r.to_dict() for r in self.results],
        }, indent=2, ensure_ascii=False)
