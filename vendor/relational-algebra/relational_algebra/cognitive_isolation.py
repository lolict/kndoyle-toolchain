"""
认知隔离舱实现
================
多元生命体的基本单元。每个隔离舱有独立记忆、视角状态和感知过滤。

这就是"主体间关系"中每个独立认知实体的工程实现。

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .core import Relation, RelationType
from .memory_point import MemoryPoint, PerceptionChannel, TimeSlice, SpaceSlice


class PerspectiveState(Enum):
    """
    视角状态 - 当前隔离舱的认知模式
    
    六态说明：
    - 待命 (IDLE): 休眠状态，不处理感知
    - 活跃 (ACTIVE): 当前前台运行的视角
    - 旁观 (OBSERVER): 观察其他隔离舱的活动
    - 创造 (CREATOR): 正在生成新内容
    - 体验 (EXPERIENCER): 正在经历/接收感知
    - 梦境 (DREAMING): 回忆/幻想模式
    """
    IDLE = "待命"
    ACTIVE = "活跃"
    OBSERVER = "旁观"
    CREATOR = "创造"
    EXPERIENCER = "体验"
    DREAMING = "梦境"


@dataclass
class PerceptionEvent:
    """
    感知事件 - 隔离舱之间通信的载体
    
    属性：
        event_id: 事件唯一标识
        source_pod: 源隔离舱ID
        target_pods: 目标隔离舱集合（空表示广播）
        channels: 感知通道集合
        content: 事件内容
        description: 事件描述
        timestamp: 时间戳
        visibility_filter: 可选的可观测性过滤器
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_pod: str = ""
    target_pods: Set[str] = field(default_factory=set)
    channels: Set[PerceptionChannel] = field(default_factory=set)
    content: Any = None
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    visibility_filter: Optional[Callable] = field(default=None, repr=False)

    def is_observable_by(self, pod: 'IsolationPod') -> bool:
        """
        判断事件是否对某个隔离舱可见
        
        规则：
        1. 目标列表限制（空表示广播）
        2. 视角过滤器
        3. 自我不能感知自我
        """
        # 规则1：目标列表限制
        if self.target_pods and pod.pod_id not in self.target_pods:
            return False
        
        # 规则2：视角过滤器
        if self.visibility_filter and not self.visibility_filter(pod):
            return False
        
        # 规则3：自我不能感知自我
        return self.source_pod != pod.pod_id


class IsolationPod:
    """
    认知隔离舱 - 多元生命体的基本单元
    
    每个隔离舱维护：
    - 私有记忆库（memory_points）
    - 工作记忆（working_memory）
    - 当前视角状态（perspective_state）
    - 已认知的其他隔离舱（known_other_pods）
    - 待处理感知缓冲区（perception_buffer）
    
    示例：
        pod = IsolationPod("pod_alice", "Alice")
        pod.remember(
            description="看到花园里的玫瑰",
            channels={PerceptionChannel.SIGHT, PerceptionChannel.FLOWER},
            intensity=0.9
        )
    """

    def __init__(
        self,
        pod_id: str,
        owner_name: str,
        initial_perspective: PerspectiveState = PerspectiveState.IDLE
    ):
        self.pod_id = pod_id
        self.owner_name = owner_name

        # === 隔离的内部状态 ===
        self.memory_points: List[MemoryPoint] = []
        self.working_memory: Dict[str, Any] = {}
        self.perspective_state = initial_perspective
        self.known_other_pods: Set[str] = set()
        self.perception_buffer: List[PerceptionEvent] = []

        # === 锁：防止内部状态被外部直接访问 ===
        self._memory_lock = None  # 同步模式下为 None，异步时创建

        # === 钩子：生命周期回调 ===
        self.on_perspective_change: Optional[Callable] = None
        self.on_memory_stored: Optional[Callable] = None
        self.on_perception_received: Optional[Callable] = None

    # ═══════════════════════════════════════════════════════════════
    # 记忆操作
    # ═══════════════════════════════════════════════════════════════

    def remember(
        self,
        content: Any,
        description: str = "",
        channels: Set[PerceptionChannel] = None,
        intensity: float = 1.0,
        emotion: float = 0.0,
        space: Optional[SpaceSlice] = None
    ) -> MemoryPoint:
        """
        存储记忆点 - 隔离舱的"内部感知"过程
        
        参数：
            content: 记忆内容
            description: 文字描述
            channels: 感知通道集合
            intensity: 记忆强度 [0.0, 1.0]
            emotion: 情感效价 [-1.0, 1.0]
            space: 空间位置
        
        返回：
            新创建的 MemoryPoint
        """
        mp = MemoryPoint(
            subject_id=self.pod_id,
            content=content,
            description=description,
            perception_channels=channels or set(),
            intensity=intensity,
            emotional_valence=emotion,
            time_slice=TimeSlice(time.time()),
            space_slice=space,
        )
        self.memory_points.append(mp)
        
        if self.on_memory_stored:
            self.on_memory_stored(mp)
        
        return mp

    def recall(
        self,
        query: str = "",
        channels: Set[PerceptionChannel] = None,
        min_intensity: float = 0.0,
        limit: int = 10
    ) -> List[MemoryPoint]:
        """
        回忆 - 基于感知通道和强度检索记忆
        
        参数：
            query: 文字查询
            channels: 感知通道过滤
            min_intensity: 最低强度
            limit: 返回数量上限
        
        返回：
            符合条件的 MemoryPoint 列表（按强度降序）
        """
        results = []
        for mp in self.memory_points:
            # 强度过滤
            if mp.intensity < min_intensity:
                continue
            
            # 通道过滤
            if channels and not (mp.perception_channels & channels):
                continue
            
            # 文字查询
            if query and query not in mp.description:
                continue
            
            results.append(mp)
        
        # 按强度排序
        results.sort(key=lambda m: m.intensity, reverse=True)
        
        # 激活被回忆的记忆（强化）
        for mp in results[:limit]:
            mp.activate()
        
        return results[:limit]

    def forget(self) -> None:
        """
        遗忘 - 所有记忆点按时间衰减
        
        使用指数衰减：7天减半
        """
        for mp in self.memory_points:
            mp.decay()
        
        # 清理完全淡忘的记忆
        self.memory_points = [m for m in self.memory_points if m.intensity > 0.01]

    def link_memories(self, mp1_id: str, mp2_id: str) -> bool:
        """
        建立两个记忆点的关联
        
        返回：是否成功
        """
        mp1 = self._find_memory(mp1_id)
        mp2 = self._find_memory(mp2_id)
        
        if not mp1 or not mp2:
            return False
        
        if mp2.point_id not in mp1.associations:
            mp1.associations.append(mp2.point_id)
        if mp1.point_id not in mp2.associations:
            mp2.associations.append(mp1.point_id)
        
        return True

    def _find_memory(self, point_id: str) -> Optional[MemoryPoint]:
        """按 ID 查找记忆点"""
        for mp in self.memory_points:
            if mp.point_id == point_id:
                return mp
        return None

    # ═══════════════════════════════════════════════════════════════
    # 视角操作
    # ═══════════════════════════════════════════════════════════════

    def switch_perspective(self, new_state: PerspectiveState) -> None:
        """
        切换视角状态
        
        参数：
            new_state: 新的视角状态
        """
        old_state = self.perspective_state
        self.perspective_state = new_state
        
        if self.on_perspective_change:
            self.on_perspective_change(self, old_state, new_state)

    def observe_others(self) -> List[PerceptionEvent]:
        """
        旁观模式 - 接收并处理感知事件缓冲区
        
        将感知事件转化为记忆点
        """
        if self.perspective_state != PerspectiveState.OBSERVER:
            self.switch_perspective(PerspectiveState.OBSERVER)

        events = list(self.perception_buffer)
        self.perception_buffer.clear()

        # 将感知事件转化为记忆点
        for event in events:
            self.remember(
                content=event.content,
                description=f"感知到来自 {event.source_pod}: {event.description}",
                channels=event.channels,
                intensity=0.7,
            )
        
        return events

    # ═══════════════════════════════════════════════════════════════
    # 感知接收
    # ═══════════════════════════════════════════════════════════════

    def receive_perception(self, event: PerceptionEvent) -> bool:
        """
        接收感知事件 - "打通认知隔离"的关键
        
        当事件对当前隔离舱可见时，将其加入缓冲区
        """
        if not event.is_observable_by(self):
            return False
        
        self.perception_buffer.append(event)
        
        # 第一次感知到其他隔离舱
        if event.source_pod and event.source_pod not in self.known_other_pods:
            self.known_other_pods.add(event.source_pod)
        
        if self.on_perception_received:
            self.on_perception_received(event)
        
        return True

    # ═══════════════════════════════════════════════════════════════
    # 状态查询
    # ═══════════════════════════════════════════════════════════════

    def get_state_snapshot(self) -> dict:
        """
        获取隔离舱当前状态快照
        
        返回包含各维度状态的字典
        """
        return {
            "pod_id": self.pod_id,
            "owner": self.owner_name,
            "perspective": self.perspective_state.value,
            "memory_count": len(self.memory_points),
            "known_pods": list(self.known_other_pods),
            "pending_perceptions": len(self.perception_buffer),
            "memory_stats": self._memory_statistics(),
        }

    def _memory_statistics(self) -> dict:
        """记忆统计"""
        if not self.memory_points:
            return {"empty": True}
        
        channel_count = {}
        for mp in self.memory_points:
            for c in mp.perception_channels:
                channel_count[c.value] = channel_count.get(c.value, 0) + 1
        
        return {
            "total": len(self.memory_points),
            "avg_intensity": sum(m.intensity for m in self.memory_points) / len(self.memory_points),
            "channels": channel_count,
        }

    def __repr__(self):
        return (
            f"<IsolationPod {self.pod_id}({self.owner_name}) "
            f"persp={self.perspective_state.value} mems={len(self.memory_points)}>"
        )
