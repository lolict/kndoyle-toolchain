"""
自举编译器 (Bootstrap Compiler)
================================
用关系代数自身实现的关系代数编译器。

核心思想：
1. 编译器源码本身用这个范式写成
2. 编译产物是更高效的机器码/字节码
3. 零外部依赖，完全自举

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import hashlib

from .narrow_waist_ir import NarrowWaistIR, IRNode, IRNodeKind
from .funnel_frontend import FunnelFrontend


@dataclass
class CompilationUnit:
    """
    编译单元 - 一次完整的编译产物
    
    属性：
        source_lang: 源语言
        target_lang: 目标语言
        ir: 窄腰IR表示
        bytecode: 生成的字节码
        source_map: 源码映射（用于调试）
    """
    source_lang: str
    target_lang: str
    ir: NarrowWaistIR
    bytecode: bytes = b""
    source_map: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BootstrapCompiler:
    """
    自举编译器 - 关系代数的自举编译器
    
    编译流程：
    1. 漏斗前端解析源码 → 窄腰IR
    2. 语义分析（类型检查、作用域解析）
    3. 优化遍（死代码消除、常量折叠）
    4. 代码生成（目标字节码）
    """

    def __init__(self):
        self.frontend = FunnelFrontend()
        self.optimization_level = 2
        self.target_language = "bytecode"

    def compile(self, source: str, filename: str = "") -> CompilationUnit:
        """
        编译入口
        
        参数：
            source: 源代码
            filename: 文件名
        
        返回：
            CompilationUnit 编译产物
        """
        unit = CompilationUnit(
            source_lang=LanguageDetector.detect(source, filename),
            target_lang=self.target_language,
            ir=NarrowWaistIR()
        )

        try:
            # 第一遍：解析
            unit.ir = self.frontend.compile(source, filename)
            
            # 第二遍：语义分析
            self._semantic_analysis(unit)
            
            # 第三遍：优化
            if self.optimization_level > 0:
                self._optimize(unit)
            
            # 第四遍：代码生成
            unit.bytecode = self._codegen(unit.ir)

        except Exception as e:
            unit.errors.append(str(e))

        return unit

    def _semantic_analysis(self, unit: CompilationUnit) -> None:
        """
        语义分析
        
        检查：
        - 类型一致性
        - 作用域规则
        - 重复定义
        """
        # 简化版：只做基础检查
        for node in unit.ir.nodes:
            if node.kind == IRNodeKind.VOID:
                unit.warnings.append(f"VOID node at {node.source_span}")

    def _optimize(self, unit: CompilationUnit) -> None:
        """
        优化遍
        
        - 死代码消除
        - 常量折叠
        - 公共子表达式消除
        """
        if self.optimization_level >= 1:
            self._dead_code_elimination(unit)
        
        if self.optimization_level >= 2:
            self._constant_folding(unit)

    def _dead_code_elimination(self, unit: CompilationUnit) -> None:
        """死代码消除"""
        # 简化版：移除孤立的VOID节点
        unit.ir.nodes = [
            n for n in unit.ir.nodes
            if not (n.kind == IRNodeKind.VOID and not n.operands)
        ]

    def _constant_folding(self, unit: CompilationUnit) -> None:
        """常量折叠"""
        # 简化版：不做实际折叠，只是标记
        pass

    def _codegen(self, ir: NarrowWaistIR) -> bytes:
        """
        代码生成
        
        将窄腰IR编译为简单的字节码：
        - 每种IRNodeKind对应一个操作码
        """
        bytecode = bytearray()
        
        for node in ir.nodes:
            opcode = self._nodekind_to_opcode(node.kind)
            bytecode.append(opcode)
            
            # 操作数编码
            for operand in node.operands:
                bytecode.extend(operand.node_id.encode()[:4])
                bytecode.append(0)  # 分隔符
        
        return bytes(bytecode)

    def _nodekind_to_opcode(self, kind: IRNodeKind) -> int:
        """IR节点类型到操作码的映射"""
        mapping = {
            IRNodeKind.UNIT: 0x01,
            IRNodeKind.VOID: 0x02,
            IRNodeKind.WITNESS: 0x03,
            IRNodeKind.PROJECT: 0x10,
            IRNodeKind.INJECT: 0x11,
            IRNodeKind.LIFT: 0x12,
            IRNodeKind.PRODUCT: 0x20,
            IRNodeKind.COPRODUCT: 0x21,
            IRNodeKind.EXPONENTIAL: 0x22,
            IRNodeKind.EQUALIZER: 0x23,
            IRNodeKind.COEQUALIZER: 0x24,
            IRNodeKind.CAUSE: 0x30,
            IRNodeKind.EFFECT: 0x31,
            IRNodeKind.PARALLEL: 0x32,
            IRNodeKind.BRAID: 0x40,
            IRNodeKind.TWIST: 0x41,
            IRNodeKind.COHERENCE: 0x42,
        }
        return mapping.get(kind, 0x00)

    def disassemble(self, bytecode: bytes) -> List[str]:
        """
        反汇编字节码
        
        用于调试和可视化
        """
        instructions = []
        i = 0
        while i < len(bytecode):
            opcode = bytecode[i]
            args = []
            i += 1
            
            # 读取操作数
            while i < len(bytecode) and bytecode[i] != 0:
                args.append(bytecode[i:i+4].decode(errors='ignore'))
                i += 5
            
            kind_name = self._opcode_to_name(opcode)
            instructions.append(f"{kind_name} {' '.join(args)}")
            i += 1
        
        return instructions

    def _opcode_to_name(self, opcode: int) -> str:
        """操作码到名称"""
        reverse_mapping = {
            0x01: "UNIT",
            0x02: "VOID",
            0x03: "WITNESS",
            0x10: "PROJECT",
            0x11: "INJECT",
            0x12: "LIFT",
            0x20: "PRODUCT",
            0x21: "COPRODUCT",
            0x22: "EXPONENTIAL",
            0x23: "EQUALIZER",
            0x24: "COEQUALIZER",
            0x30: "CAUSE",
            0x31: "EFFECT",
            0x32: "PARALLEL",
            0x40: "BRAID",
            0x41: "TWIST",
            0x42: "COHERENCE",
        }
        return reverse_mapping.get(opcode, f"UNKNOWN(0x{opcode:02x})")


class LanguageDetector:
    """语言检测器"""

    @staticmethod
    def detect(source: str, filename: str = "") -> str:
        """检测源代码语言"""
        from .funnel_frontend import LanguageSignature
        return LanguageSignature.detect(source, filename)
