# -*- coding: utf-8 -*-
"""
局部文件系统关系代数处理器
Local Filesystem Relational Algebra Processor

功能：
1. 扫描目录内所有文本文件（.txt/.md/.py/.json/.csv/.toml）
2. 构建文档关系网络（主体/客体/时间戳/标签/内容指纹）
3. 增量摘要写入（不覆盖原文，新建 .rel-summary 文件）
4. 全量感知：每一份文档都是观测对象，进入漏斗统计

哲学对应：
- 漏斗  = 文件扫描 → 关系抽取 → 收敛摘要
- 观测者 = 每个文件作为独立存在单元，被观测并打标签
- 税务筛选 = 高频词/核心段落 = 有效信息 = 交税
- 统计锥  = 摘要随时间积累，形成视角切片的历史锥
- 夫妻共同体 = 原文(阴) + 摘要(阳) = 满全态
"""

import os
import re
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter


@dataclass
class 文档观测者:
    """单个文档的观测记录"""
    文件路径: str
    观测时间: str
    内容指纹: str          # SHA256摘要，文档唯一标识
    词频统计: Dict[str, int] = field(default_factory=dict)
    标签集合: Set[str] = field(default_factory=set)
    摘要文本: str = ""    # 由漏斗收敛后的核心内容
    税务评级: str = "pending"  # pending / low / medium / high
    相位切片: int = 0    # 读取时的逻辑时间切片


@dataclass
class 关系网络:
    """文档间关系网络"""
    共现词矩阵: Dict[str, Dict[str, int]] = field(default_factory=dict)
    时序关系: List[Tuple[str, str, str]] = field(default_factory=list)  # (文件A, 文件B, 共现词)
    层级依赖: Dict[str, List[str]] = field(default_factory=dict)       # 文件 → 关联文件列表


class 文件漏斗路由器:
    """
    漏斗降维：文件流 → 词频过滤 → 核心抽取 → 摘要收敛
    """

    def __init__(self, 高频阈值: int = 5, 低频阈值: int = 1):
        self.高频阈值 = 高频阈值
        self.低频阈值 = 低频阈值

    def 统计词频(self, 文本: str) -> Counter:
        """二元观测：分词并统计"""
        词序列 = re.findall(r'[\w\u4e00-\u9fff]{2,}', 文本)
        return Counter(词序列)

    def 税务筛选(self, 词频: Counter) -> Tuple[Set[str], Set[str]]:
        """
        税务筛选：高频词=高价值资产（交税），低频词=边缘资产（免税）
        返回：(应税词集合, 免税词集合)
        """
        应税词 = {词 for 词, 频次 in 词频.items() if 频次 >= self.高频阈值}
        免税词 = {词 for 词, 频次 in 词频.items() if 频次 <= self.低频阈值}
        return 应税词, 免税词

    def 收敛摘要(self, 文本: str, 词频: Counter, 最大句数: int = 3) -> str:
        """
        满全法收敛：找到包含高频词最多的句子，提取为摘要
        摘要 = 原文的核心税务 = 高价值信息的聚合体
        """
        句子序列 = re.split(r'[。！？\n]+', 文本)
        应税词, _ = self.税务筛选(词频)

        if not 应税词:
            return 文本[:200] if len(文本) > 200 else 文本

        句子评分 = []
        for 句子 in 句子序列:
            句子词 = set(re.findall(r'[\w\u4e00-\u9fff]{2,}', 句子))
            分数 = len(句子词 & 应税词)
            if 分数 > 0:
                句子评分.append((分数, 句子))

        句子评分.sort(key=lambda x: x[0], reverse=True)
        核心句 = [s for _, s in 句子评分[:最大句数]]
        return '。'.join(核心句) + '。'

    def 税务评级(self, 词频: Counter, 总词数: int) -> str:
        """根据词频密度判断税务评级"""
        if 总词数 == 0:
            return "low"
        有效词数 = sum(1 for 词, 频 in 词频.items() if 频 >= self.高频阈值)
        密度 = 有效词数 / 总词数
        if 密度 > 0.3:
            return "high"
        elif 密度 > 0.1:
            return "medium"
        return "low"


class 文件观测者系统:
    """
    认知观测者：扫描目录，观测每一份文档，建立关系网络
    """

    支持后缀 = {'.txt', '.md', '.py', '.json', '.csv', '.toml', '.yaml', '.yml'}

    def __init__(self, 工作目录: str, 输出目录: Optional[str] = None):
        self.工作目录 = Path(工作目录)
        self.输出目录 = (Path(输出目录) if 输出目录 else self.工作目录 / ".rel_output")
        self.输出目录.mkdir(exist_ok=True)
        self.漏斗 = 文件漏斗路由器()
        self.观测记录: List[文档观测者] = []
        self.关系网络 = 关系网络()
        self.全局词频 = Counter()
        self.时间切片计数器 = 0

    def 内容指纹(self, 内容: str) -> str:
        """生成内容唯一指纹"""
        return hashlib.sha256(内容.encode('utf-8')).hexdigest()[:16]

    def 读取文档(self, 文件路径: Path) -> Optional[str]:
        """读取文档内容，二进制检测"""
        try:
            with open(文件路径, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(文件路径, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception:
                return None
        except Exception:
            return None

    def 观测单个文档(self, 文件路径: Path) -> Optional[文档观测者]:
        """三元裁判观测：读取→统计→收敛→评级"""
        内容 = self.读取文档(文件路径)
        if 内容 is None:
            return None

        词频 = self.漏斗.统计词频(内容)
        总词数 = sum(词频.values())
        摘要 = self.漏斗.收敛摘要(内容, 词频)
        评级 = self.漏斗.税务评级(词频, 总词数)
        指纹 = self.内容指纹(内容)

        观测 = 文档观测者(
            文件路径=str(文件路径),
            观测时间=datetime.now().isoformat(),
            内容指纹=指纹,
            词频统计=dict(词频.most_common(50)),
            摘要文本=摘要,
            税务评级=评级,
            相位切片=self.时间切片计数器
        )
        return 观测

    def 构建共现矩阵(self, 文档列表: List[文档观测者]):
        """二元博弈：统计文档间共现词，构建关系网络"""
        词频到文档 = {}
        for doc in 文档列表:
            for 词 in doc.词频统计.keys():
                if 词 not in 词频到文档:
                    词频到文档[词] = []
                词频到文档[词].append(doc.文件路径)

        # 高频词构建共现关系
        高频词 = {词 for 词, 文档列表 in 词频到文档.items() if len(文档列表) >= 2}
        for 词 in 高频词:
            文档集 = 词频到文档[词]
            for i in range(len(文档集)):
                for j in range(i + 1, len(文档集)):
                    self.关系网络.共现词矩阵.setdefault(文档集[i], {})[文档集[j]] = \
                        self.关系网络.共现词矩阵.setdefault(文档集[j], {}).get(文档集[i], 0) + 1

    def 全量扫描(self) -> List[文档观测者]:
        """
        漏斗入口：扫描工作目录所有文本文件
        返回所有文档的观测记录
        """
        扫描结果 = []
        文件列表 = list(self.工作目录.rglob("*"))
        文件列表 = [f for f in 文件列表 if f.is_file() and f.suffix.lower() in self.支持后缀]

        for 文件路径 in 文件列表:
            # 跳过自身输出目录
            if str(self.输出目录) in str(文件路径):
                continue

            观测 = self.观测单个文档(文件路径)
            if 观测:
                扫描结果.append(观测)
                self.全局词频.update(观测.词频统计)
                self.时间切片计数器 += 1

        self.观测记录 = 扫描结果
        self.构建共现矩阵(扫描结果)
        return 扫描结果

    def 写入摘要文件(self, 观测: 文档观测者) -> Path:
        """
        夫妻共同体写入：原文(阴) + 摘要(阳) = 完整记录
        摘要写入 .rel-summary 文件，不覆盖原文
        """
        原文路径 = Path(观测.文件路径)
        摘要文件名 = 原文路径.stem + ".rel-summary.md"
        摘要路径 = self.输出目录 / 摘要文件名

        内容块 = f"""# 关系代数摘要报告

## 原文
{观测.文件路径}

## 观测时间
{观测.观测时间}

## 相位切片
#{观测.相位切片}

## 税务评级
**{观测.税务评级.upper()}** 级

## 核心税务词 (高频词 Top20)
{json.dumps(list(观测.词频统计.keys())[:20], ensure_ascii=False, indent=2)}

## 摘要 (收敛后)
{观测.摘要文本}

## 内容指纹
`{观测.内容指纹}`

---
*由 主体间关系代数处理器 生成 | 漏斗降维收敛*
"""
        with open(摘要路径, 'w', encoding='utf-8') as f:
            f.write(内容块)
        return 摘要路径

    def 生成统计报告(self) -> Path:
        """
        统计锥报告：全局词频 + 关系网络 + 税务汇总
        """
        报告路径 = self.输出目录 / "rel-statistics.md"
        高频全局 = self.全局词频.most_common(30)

        # 统计各评级分布
        评级分布 = Counter(doc.税务评级 for doc in self.观测记录)

        内容 = f"""# 统计锥报告

## 全局观测统计

- **扫描文档数**: {len(self.观测记录)}
- **全局词种数**: {len(self.全局词频)}
- **总词频数**: {sum(self.全局词频.values())}
- **时间切片数**: {self.时间切片计数器}

## 税务评级分布

| 评级 | 文档数 | 说明 |
|------|--------|------|
| HIGH | {评级分布.get('high', 0)} | 高密度有效信息，税务大户 |
| MEDIUM | {评级分布.get('medium', 0)} | 中等密度，需关注 |
| LOW | {评级分布.get('low', 0)} | 低密度，可能为边缘内容 |
| PENDING | {评级分布.get('pending', 0)} | 未评定 |

## 全局高频词 Top30

"""
        for 词, 频次 in 高频全局:
            条形 = "█" * min(频次, 30)
            内容 += f"- **{词}**: {频次} {条形}\n"

        内容 += "\n## 文档关系网络（Top10共现对）\n\n"
        共现对列表 = []
        for 文件A, 邻居 in self.关系网络.共现词矩阵.items():
            for 文件B, 次数 in 邻居.items():
                if 文件A < 文件B:
                    共现对列表.append((次数, Path(文件A).name, Path(文件B).name))
        共现对列表.sort(reverse=True)

        for 次数, 名称A, 名称B in 共现对列表[:10]:
            内容 += f"- {名称A} ↔ {名称B} (共现 {次数} 次)\n"

        with open(报告路径, 'w', encoding='utf-8') as f:
            f.write(内容)
        return 报告路径

    def 全量处理并输出(self) -> Dict[str, any]:
        """
        完整流水线：扫描 → 观测 → 写入摘要 → 生成报告
        返回处理结果摘要
        """
        扫描结果 = self.全量扫描()
        摘要路径列表 = []
        for 观测 in 扫描结果:
            路径 = self.写入摘要文件(观测)
            摘要路径列表.append(str(路径))

        报告路径 = self.生成统计报告()

        return {
            "扫描文档数": len(扫描结果),
            "摘要文件路径": 摘要路径列表,
            "统计报告路径": str(报告路径),
            "税务大户": [
                {"文件": Path(doc.文件路径).name, "评级": doc.税务评级, "高频词数": len(doc.词频统计)}
                for doc in sorted(扫描结果, key=lambda x: len(x.词频统计), reverse=True)[:5]
            ]
        }


def main(工作目录: Optional[str] = None):
    """
    命令行入口
    用法: python local_processor.py [工作目录路径]
    """
    import sys
    目录 = sys.argv[1] if len(sys.argv) > 1 else "../../relational_algebra" if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(__file__))
    print(f"🔍 启动文件观测者系统")
    print(f"📁 工作目录: {目录}")
    系统 = 文件观测者系统(工作目录=目录)
    结果 = 系统.全量处理并输出()
    print(f"\n✅ 处理完成:")
    print(f"   扫描文档: {结果['扫描文档数']} 份")
    print(f"   摘要生成: {len(结果['摘要文件路径'])} 份")
    print(f"   报告: {结果['统计报告路径']}")
    print(f"\n🏆 税务大户 Top5:")
    for item in 结果['税务大户']:
        print(f"   [{item['评级'].upper()}] {item['文件']} ({item['高频词数']}词)")
    return 结果


if __name__ == "__main__":
    main()
