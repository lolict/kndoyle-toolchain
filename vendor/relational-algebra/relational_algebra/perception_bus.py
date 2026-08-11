"""
感知总线实现
============
隔离舱之间的通信通道。这就是"认知隔离被打破"的发生点。

事件在总线上流动，只有符合可观测性规则的隔离舱才能"看到"事件。

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from typing import Callable, Dict, List, Set
import asyncio

from .cognitive_isolation import IsolationPod, PerceptionEvent
from .memory_point import PerceptionChannel


class PerceptionBus:
    """
    感知总线 - 隔离舱之间的事件传递中介
    
    核心功能：
    1. 注册/注销隔离舱
    2. 发送感知事件（emit/emit_sync）
    3. 广播事件到所有隔离舱
    4. 事件历史查询
    5. 事件订阅（钩子回调）
    
    示例：
        bus = PerceptionBus()
        bus.register(pod_alice)
        bus.register(pod_bob)
        
        # 发送事件
        event = bus.broadcast("pod_alice", "看到Bob在笑")
        print(f"接收到事件的隔离舱: {[p.pod_id for p in event.observers]}")
    """

    def __init__(self):
        self.pods: Dict[str, IsolationPod] = {}
        self.event_log: List[PerceptionEvent] = []
        self.subscribers: Dict[str, List[Callable]] = {}

    def register(self, pod: IsolationPod) -> None:
        """
        注册隔离舱到总线
        
        参数：
            pod: IsolationPod 实例
        """
        self.pods[pod.pod_id] = pod

    def unregister(self, pod_id: str) -> None:
        """
        注销隔离舱
        
        参数：
            pod_id: 隔离舱ID
        """
        if pod_id in self.pods:
            del self.pods[pod_id]

    async def emit(self, event: PerceptionEvent) -> List[IsolationPod]:
        """
        异步发送感知事件
        
        参数：
            event: 感知事件
        
        返回：
            接收到事件的隔离舱列表
        """
        # 记录到事件日志
        self.event_log.append(event)

        # 找出能感知到事件的隔离舱
        observers = []
        for pod in self.pods.values():
            if pod.receive_perception(event):
                observers.append(pod)
                # 触发订阅回调
                if pod.pod_id in self.subscribers:
                    for cb in self.subscribers[pod.pod_id]:
                        cb(event)

        return observers

    def emit_sync(self, event: PerceptionEvent) -> List[IsolationPod]:
        """
        同步发送感知事件
        
        这是默认的广播语义。
        
        参数：
            event: 感知事件
        
        返回：
            接收到事件的隔离舱列表
        """
        self.event_log.append(event)
        observers = []
        for pod in self.pods.values():
            if pod.receive_perception(event):
                observers.append(pod)
        return observers

    def subscribe(self, pod_id: str, callback: Callable) -> None:
        """
        订阅事件 - 为指定隔离舱添加回调
        
        参数：
            pod_id: 隔离舱ID
            callback: 回调函数，签名为 (PerceptionEvent) -> None
        """
        if pod_id not in self.subscribers:
            self.subscribers[pod_id] = []
        self.subscribers[pod_id].append(callback)

    def unsubscribe(self, pod_id: str, callback: Callable) -> None:
        """
        取消订阅
        
        参数：
            pod_id: 隔离舱ID
            callback: 要移除的回调函数
        """
        if pod_id in self.subscribers:
            self.subscribers[pod_id] = [
                cb for cb in self.subscribers[pod_id] if cb != callback
            ]

    def broadcast(
        self,
        source_pod_id: str,
        description: str,
        content=None,
        channels: Set[PerceptionChannel] = None
    ) -> PerceptionEvent:
        """
        广播事件到所有隔离舱
        
        参数：
            source_pod_id: 源隔离舱ID
            description: 事件描述
            content: 事件内容
            channels: 感知通道集合
        
        返回：
            创建的感知事件
        """
        event = PerceptionEvent(
            source_pod=source_pod_id,
            description=description,
            content=content,
            channels=channels or set(),
        )
        self.emit_sync(event)
        return event

    def direct_message(
        self,
        source_pod_id: str,
        target_pod_id: str,
        description: str,
        content=None,
        channels: Set[PerceptionChannel] = None
    ) -> PerceptionEvent:
        """
        定向消息 - 只发送给指定隔离舱
        
        参数：
            source_pod_id: 源隔离舱ID
            target_pod_id: 目标隔离舱ID
            description: 消息描述
            content: 消息内容
            channels: 感知通道集合
        
        返回：
            创建的感知事件
        """
        event = PerceptionEvent(
            source_pod=source_pod_id,
            target_pods={target_pod_id},
            description=description,
            content=content,
            channels=channels or set(),
        )
        self.emit_sync(event)
        return event

    def event_history(self, pod_id: str = None) -> List[PerceptionEvent]:
        """
        获取事件历史
        
        参数：
            pod_id: 可选，指定隔离舱（返回发出或接收的事件）
        
        返回：
            事件列表
        """
        if pod_id is None:
            return list(self.event_log)
        
        return [
            e for e in self.event_log
            if e.source_pod == pod_id or pod_id in e.target_pods
        ]

    def clear_history(self) -> None:
        """清空事件历史"""
        self.event_log.clear()

    def get_pods(self) -> List[IsolationPod]:
        """获取所有注册的隔离舱"""
        return list(self.pods.values())

    def __repr__(self):
        return f"<PerceptionBus pods={len(self.pods)} events={len(self.event_log)}>"
