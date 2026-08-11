"""
感知通道枚举 - 50种感知模态
============================
记忆点的感知通道定义，按层次分为6大类：

第一层：基础感官（5种）
第二层：身体状态（10种）  
第三层：情感（5种）
第四层：抽象认知（12种）
第五层：场域（5种）
第六层：社会与想象（13种）

总计：50种感知通道

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Set, Optional
import time
import math


class PerceptionChannel(Enum):
    """
    感知通道 - 记忆的模态算子
    
    50种感知通道分类：
    
    【第一层：基础感官】
    - SIGHT: 视觉（感知眼）
    - HEARING: 听觉（感知耳）
    - SMELL: 嗅觉（感知嗅）
    - TASTE: 味觉（感知味）
    - TOUCH: 触觉（感知触）
    
    【第二层：身体状态】
    - HUNGER: 饥饿感
    - THIRST: 口渴感
    - FATIGUE: 疲劳感
    - SLEEP: 困倦感
    - PAIN: 疼痛感
    - WARMTH: 温暖感
    - COLDNESS: 寒冷感
    - ILLNESS: 疾病感
    - WEIGHT: 重量感
    - BALANCE: 平衡感
    
    【第三层：情感】
    - EMOTION: 情感（总类）
    - INTIMACY: 亲密感
    - DISTANCE: 距离感
    - PLEASURE: 愉悦感
    - BADNESS: 不适感
    
    【第四层：抽象认知】
    - ETHICS: 伦理感知
    - PSYCHOLOGY: 心理感知
    - PHYSIOLOGY: 生理感知
    - COMMON_SENSE: 常识感知
    - RIGHT_WRONG: 是非感知
    - QUANTITY: 数量感知
    - CLUMSINESS: 笨拙感
    - HUMOR: 幽默感
    - BANTER: 调侃感
    - FUN: 趣味感
    - EMBARRASSMENT: 尴尬感
    
    【第五层：场域】
    - FIELD: 场域感知
    - TIME_SPACE: 时空感知
    - ENVIRONMENT: 环境感知
    - TEMPERATURE: 温度感知
    - NATURE: 自然感知
    
    【第六层：社会与想象】
    - FAMILY: 家庭感知
    - PERSON: 人物感知
    - OBJECT: 物体感知
    - INSECT: 昆虫感知
    - GRASS: 草感知
    - TREE: 树感知
    - FLOWER: 花感知
    - BEAST: 野兽感知
    - FANTASY: 幻想感知
    - TASTE_SENSE: 独立味觉
    """
    # 第一层:基础感官
    SIGHT = "感知眼"
    HEARING = "感知耳"
    SMELL = "感知嗅"
    TASTE = "感知味"
    TOUCH = "感知触"

    # 第二层:身体状态
    HUNGER = "感知饿"
    THIRST = "感知渴"
    FATIGUE = "感知累"
    SLEEP = "感知困"
    PAIN = "感知痛"
    WARMTH = "感知温"
    COLDNESS = "感知寒"
    ILLNESS = "感知病"
    WEIGHT = "感知重"
    BALANCE = "感知配重"

    # 第三层:情感
    EMOTION = "感知情"
    INTIMACY = "感知亲"
    DISTANCE = "感知疏"
    PLEASURE = "感知爽"
    BADNESS = "感知坏"

    # 第四层:抽象认知
    ETHICS = "感知伦理"
    PSYCHOLOGY = "感知心理"
    PHYSIOLOGY = "感知生理"
    COMMON_SENSE = "感知常识"
    RIGHT_WRONG = "感知对错"
    QUANTITY = "感知量"
    CLUMSINESS = "感知笨"
    HUMOR = "感知幽默"
    BANTER = "感知侃"
    FUN = "感知趣"
    EMBARRASSMENT = "感知糗"

    # 第五层:场域
    FIELD = "感知场"
    TIME_SPACE = "感知时空"
    ENVIRONMENT = "感知环境"
    TEMPERATURE = "感知气温"
    NATURE = "感知自然"

    # 第六层:社会与想象
    FAMILY = "感知家"
    PERSON = "感知人"
    OBJECT = "感知物"
    INSECT = "感知虫"
    GRASS = "感知草"
    TREE = "感知树"
    FLOWER = "感知花"
    BEAST = "感知兽"
    FANTASY = "感知幻想"
    TASTE_SENSE = "感知味觉"

    @classmethod
    def get_by_layer(cls, layer: int) -> List['PerceptionChannel']:
        """按层次获取感知通道"""
        layers = {
            1: [cls.SIGHT, cls.HEARING, cls.SMELL, cls.TASTE, cls.TOUCH],
            2: [cls.HUNGER, cls.THIRST, cls.FATIGUE, cls.SLEEP, cls.PAIN,
                cls.WARMTH, cls.COLDNESS, cls.ILLNESS, cls.WEIGHT, cls.BALANCE],
            3: [cls.EMOTION, cls.INTIMACY, cls.DISTANCE, cls.PLEASURE, cls.BADNESS],
            4: [cls.ETHICS, cls.PSYCHOLOGY, cls.PHYSIOLOGY, cls.COMMON_SENSE,
                cls.RIGHT_WRONG, cls.QUANTITY, cls.CLUMSINESS, cls.HUMOR,
                cls.BANTER, cls.FUN, cls.EMBARRASSMENT],
            5: [cls.FIELD, cls.TIME_SPACE, cls.ENVIRONMENT, cls.TEMPERATURE, cls.NATURE],
            6: [cls.FAMILY, cls.PERSON, cls.OBJECT, cls.INSECT, cls.GRASS,
                cls.TREE, cls.FLOWER, cls.BEAST, cls.FANTASY, cls.TASTE_SENSE],
        }
        return layers.get(layer, [])

    @classmethod
    def total_count(cls) -> int:
        """获取总通道数"""
        return len(cls.__members__)


@dataclass
class TimeSlice:
    """
    时间切片 - 记忆的时间坐标
    
    属性：
        timestamp: Unix 时间戳
        duration: 持续时间（秒）
    """
    timestamp: float
    duration: float = 0.0

    def distance_to(self, other: 'TimeSlice') -> float:
        """时间距离（秒）"""
        return abs(self.timestamp - other.timestamp)

    def __repr__(self):
        return f"TimeSlice(t={self.timestamp:.2f}, d={self.duration})"


@dataclass
class SpaceSlice:
    """
    空间切片 - 记忆的空间坐标
    
    属性：
        location: 文字位置描述
        coordinates: 三维坐标 (x, y, z)
    """
    location: str
    coordinates: tuple = (0.0, 0.0, 0.0)

    def same_place(self, other: 'SpaceSlice', threshold: float = 1.0) -> bool:
        """是否同处一地"""
        if self.location and other.location:
            return self.location == other.location
        dist = math.sqrt(
            sum((a - b) ** 2 for a, b in zip(self.coordinates, other.coordinates))
        )
        return dist < threshold


@dataclass
class MemoryPoint:
    """
    记忆点 - 主体间关系代数的原子
    
    这是最小的记忆单元，不可再分。
    
    属性：
        point_id: 记忆点唯一ID
        subject_id: 所属隔离舱ID
        time_slice: 时间坐标
        space_slice: 空间坐标（可选）
        perception_channels: 感知通道集合
        content: 记忆内容
        description: 文字描述
        intensity: 记忆强度 [0.0, 1.0]
        emotional_valence: 情感效价 [-1.0, 1.0]
        associations: 关联的记忆点ID列表
        access_count: 访问次数
        last_accessed: 上次访问时间
    """
    subject_id: str
    point_id: str = field(default_factory=lambda: f"mp_{int(time.time()*1e6)}")
    time_slice: TimeSlice = field(default_factory=lambda: TimeSlice(time.time()))
    space_slice: Optional[SpaceSlice] = None
    perception_channels: Set[PerceptionChannel] = field(default_factory=set)
    content: Any = None
    description: str = ""
    intensity: float = 1.0
    emotional_valence: float = 0.0
    associations: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def decay(self) -> None:
        """
        遗忘 - 强度随时间衰减
        
        使用指数衰减：7天减半
        """
        elapsed = time.time() - self.last_accessed
        self.intensity *= math.exp(-elapsed / (7 * 24 * 3600))

    def activate(self) -> None:
        """
        激活 - 访问记忆时增强
        """
        self.access_count += 1
        self.last_accessed = time.time()
        self.intensity = min(1.0, self.intensity * 1.1)

    def channel_overlap(self, other: 'MemoryPoint') -> float:
        """
        通道重叠度 - Jaccard 相似度
        """
        if not self.perception_channels or not other.perception_channels:
            return 0.0
        intersection = self.perception_channels & other.perception_channels
        union = self.perception_channels | other.perception_channels
        return len(intersection) / len(union)

    def temporal_proximity(self, other: 'MemoryPoint') -> float:
        """
        时间邻近度 - 指数衰减，1小时内高度相关
        """
        dist = self.time_slice.distance_to(other.time_slice)
        return math.exp(-dist / 3600)

    def spatial_proximity(self, other: 'MemoryPoint') -> float:
        """
        空间邻近度
        """
        if self.space_slice is None or other.space_slice is None:
            return 0.5  # 未知空间，中性
        if self.space_slice.same_place(other.space_slice):
            return 1.0
        return 0.0

    def connection_strength(self, other: 'MemoryPoint') -> float:
        """
        综合关联强度 - 加权平均
        
        权重：通道 40%，时间 20%，空间 20%，情感 20%
        """
        channel = self.channel_overlap(other)
        temporal = self.temporal_proximity(other)
        spatial = self.spatial_proximity(other)
        emotional = 1.0 - abs(self.emotional_valence - other.emotional_valence) / 2
        
        return (channel * 0.4 + temporal * 0.2 +
                spatial * 0.2 + emotional * 0.2)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "point_id": self.point_id,
            "subject_id": self.subject_id,
            "time": self.time_slice.timestamp,
            "channels": [c.value for c in self.perception_channels],
            "description": self.description,
            "intensity": self.intensity,
            "emotion": self.emotional_valence,
            "associations": self.associations,
        }

    def __repr__(self):
        channels = ",".join(c.value for c in self.perception_channels)
        return f"[{self.subject_id}|{channels}|{self.description}|i={self.intensity:.2f}]"
