"""
漏斗前端 (Funnel Frontend)
===========================
漏斗大开口：接收任意编程语言的源码，
通过语言识别 → 语法解析 → IR降维 → 同伦合并，
输出窄腰 IR 节点序列。

作者：莫刘连理萝莉兰零离
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

from .narrow_waist_ir import NarrowWaistIR, IRNode, IRNodeKind


@dataclass
class LanguageSignature:
    """
    编程语言签名：从语法特征识别语言
    
    属性：
        name: 语言名称
        extensions: 文件扩展名列表
        keywords: 关键词及其权重
        syntax_patterns: 语法模式（regex）
        semantic_footprint: 语义轮廓
        paradigm_weight: 范式权重
    """
    name: str
    extensions: List[str]
    keywords: Dict[str, float]
    syntax_patterns: Dict[str, str]
    semantic_footprint: str
    paradigm_weight: Dict[str, float]

    @staticmethod
    def detect(source_code: str, filename: str = "") -> str:
        """
        从源码内容自动识别语言
        
        使用关键词扫描和扩展名匹配。
        """
        scores: Dict[str, float] = {}
        
        signatures = [
            # Python
            LanguageSignature(
                name="python",
                extensions=[".py"],
                keywords={"def ": 0.9, "import ": 0.8, "self.": 0.7, "elif": 0.9, "lambda": 0.8},
                syntax_patterns={"indent": r"^\s{4}", "decorator": r"^@\w+"},
                semantic_footprint="multi-paradigm",
                paradigm_weight={"functional": 0.6, "imperative": 0.5, "oo": 0.8}
            ),
            # JavaScript
            LanguageSignature(
                name="javascript",
                extensions=[".js", ".mjs"],
                keywords={"function ": 0.8, "const ": 0.9, "let ": 0.9, "async": 0.7},
                syntax_patterns={"arrow": "=>", "template": r"`\$\{"},
                semantic_footprint="prototype-oo",
                paradigm_weight={"functional": 0.8, "imperative": 0.6, "oo": 0.5}
            ),
            # Rust
            LanguageSignature(
                name="rust",
                extensions=[".rs"],
                keywords={"fn ": 0.9, "let mut": 0.9, "impl ": 0.8, "pub fn": 0.9, "->": 0.9},
                syntax_patterns={"ownership": r"&mut|::|<", "pattern": r"match\s+\w+\s+\{"},
                semantic_footprint="systems-functional",
                paradigm_weight={"functional": 0.7, "imperative": 0.5, "systems": 0.9}
            ),
            # Go
            LanguageSignature(
                name="go",
                extensions=[".go"],
                keywords={"func ": 0.9, "package ": 0.9, "import (": 0.9, ":=": 0.8},
                syntax_patterns={"goroutine": r"go\s+\w+\(", "channel": r"<-\s*\w+"},
                semantic_footprint="concurrent-imperative",
                paradigm_weight={"concurrent": 0.9, "imperative": 0.8, "functional": 0.4}
            ),
            # Haskell
            LanguageSignature(
                name="haskell",
                extensions=[".hs", ".lhs"],
                keywords={"module ": 0.8, "data ": 0.9, "where": 0.9, "::": 0.9},
                syntax_patterns={"type_sig": r"::\s*\w+", "do_notation": r"do\s+\w+"},
                semantic_footprint="pure-functional",
                paradigm_weight={"functional": 1.0, "lazy": 0.9, "type": 1.0}
            ),
            # C
            LanguageSignature(
                name="c",
                extensions=[".c", ".h"],
                keywords={"#include": 0.9, "int main": 0.8, "printf": 0.7},
                syntax_patterns={"pointer": r"\*\w+", "preprocessor": r"^\s*#\w+"},
                semantic_footprint="systems-imperative",
                paradigm_weight={"systems": 0.9, "imperative": 1.0, "low_level": 1.0}
            ),
            # 关系代数语言
            LanguageSignature(
                name="relational",
                extensions=[".rel", ".dl", ".pl"],
                keywords={"INPUT": 0.9, "OUTPUT": 0.9, "decl": 0.9, "query": 0.9, ":-": 0.9},
                syntax_patterns={"rule": r":-", "tuple": r"<.+,.+>"},
                semantic_footprint="relational-declarative",
                paradigm_weight={"relational": 1.0, "declarative": 1.0, "logic": 0.9}
            ),
        ]

        for sig in signatures:
            score = 0.0
            # 扩展名匹配
            for ext in sig.extensions:
                if filename.endswith(ext):
                    score += 2.0
            # 关键词扫描
            for kw, weight in sig.keywords.items():
                if kw in source_code:
                    score += weight
            if score > 0:
                scores[sig.name] = score

        if not scores:
            return "unknown"
        return max(scores, key=scores.get)


@dataclass
class ParseResult:
    """解析结果：标准化 AST + 语言标签"""
    language: str
    raw_tree: Dict[str, Any]
    standard_ast: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    complexity: float = 0.0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)


class FunnelFrontend:
    """
    漏斗前端 - 多语言到窄腰IR的转换器
    
    流程：
    1. 语言识别（LanguageSignature.detect）
    2. 语法解析（LanguageParser）
    3. AST标准化（standard_ast）
    4. IR降维（NarrowWaistIR.emit）
    5. 同伦合并（漏斗压缩）
    """

    def __init__(self):
        self.ir_builder = NarrowWaistIR()

    def compile(self, source: str, filename: str = "") -> NarrowWaistIR:
        """
        编译入口：从源码到窄腰IR
        
        参数：
            source: 源代码
            filename: 文件名（用于扩展名识别）
        
        返回：
            NarrowWaistIR 实例
        """
        # 第一步：语言识别
        language = LanguageSignature.detect(source, filename)
        
        # 第二步：语法解析
        parser = LanguageParser()
        parse_result = parser.parse(source, language, filename)
        
        # 第三步：转换为IR
        self._ast_to_ir(parse_result.standard_ast, language)
        
        return self.ir_builder

    def _ast_to_ir(self, ast: Dict[str, Any], language: str) -> None:
        """AST转换为窄腰IR"""
        if ast.get("kind") == "program":
            for node in ast.get("nodes", []):
                self._node_to_ir(node, language)
        elif ast.get("kind") == "function_def":
            self._emit_function_def(ast, language)
        elif ast.get("kind") == "type_def":
            self._emit_type_def(ast, language)

    def _node_to_ir(self, node: Dict[str, Any], language: str) -> None:
        """单个节点转换为IR"""
        kind = node.get("kind", "")
        
        if kind == "function_def":
            self._emit_function_def(node, language)
        elif kind == "import":
            self.ir_builder.unit(node.get("target", ""))
        elif kind == "variable_def":
            self.ir_builder.unit(node.get("name", ""))

    def _emit_function_def(self, node: Dict[str, Any], language: str) -> IRNode:
        """发射函数定义"""
        name = node.get("name", "anonymous")
        return self.ir_builder.emit(
            IRNodeKind.UNIT,
            label=f"func:{name}",
            source_lang=language,
            source_span=node.get("span", "")
        )

    def _emit_type_def(self, node: Dict[str, Any], language: str) -> IRNode:
        """发射类型定义"""
        name = node.get("name", "T")
        return self.ir_builder.emit(
            IRNodeKind.UNIT,
            label=f"type:{name}",
            source_lang=language,
            source_span=node.get("span", "")
        )


class LanguageParser:
    """语言解析器：每种语言有独立的解析策略"""

    def __init__(self):
        self.parsers: Dict[str, Callable[[str, str], ParseResult]] = {
            "python": self._parse_python,
            "javascript": self._parse_javascript,
            "rust": self._parse_rust,
            "go": self._parse_go,
            "haskell": self._parse_haskell,
            "c": self._parse_c,
            "relational": self._parse_relational,
        }

    def parse(self, source: str, language: Optional[str] = None, filename: str = "") -> ParseResult:
        """主解析入口"""
        if language is None:
            language = LanguageSignature.detect(source, filename)

        if language not in self.parsers:
            return ParseResult(
                language=language,
                raw_tree={},
                standard_ast={"kind": "error", "msg": f"Unsupported language: {language}"},
                nodes=[]
            )

        return self.parsers[language](source, filename)

    def _parse_python(self, source: str, filename: str) -> ParseResult:
        """Python解析器（简化版）"""
        result = ParseResult(language="python", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            node = self._classify_python_line(stripped, i + 1)
            if node:
                result.nodes.append(node)

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _classify_python_line(self, line: str, lineno: int) -> Optional[Dict]:
        """Python行分类"""
        span = f"{lineno}:1-{lineno}:{len(line)}"
        if line.startswith("def "):
            name = line.split("(")[0].split()[1] if "(" in line else "anonymous"
            return {"kind": "function_def", "span": span, "name": name}
        elif line.startswith("class "):
            name = line.split(":")[0].split()[1] if ":" in line else "T"
            return {"kind": "type_def", "span": span, "name": name}
        elif line.startswith("import ") or line.startswith("from "):
            target = line.split()[1] if len(line.split()) > 1 else ""
            return {"kind": "import", "span": span, "target": target}
        return {"kind": "expr", "span": span}

    def _parse_javascript(self, source: str, filename: str) -> ParseResult:
        """JavaScript解析器（简化版）"""
        result = ParseResult(language="javascript", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if "function " in stripped or "=>" in stripped:
                result.nodes.append({"kind": "function_def", "span": span, "name": "func"})
            elif stripped.startswith("const ") or stripped.startswith("let "):
                result.nodes.append({"kind": "variable_def", "span": span})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _parse_rust(self, source: str, filename: str) -> ParseResult:
        """Rust解析器（简化版）"""
        result = ParseResult(language="rust", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if "fn " in stripped and "(" in stripped:
                result.nodes.append({"kind": "function_def", "span": span, "name": "func"})
            elif "struct " in stripped or "enum " in stripped or "trait " in stripped:
                result.nodes.append({"kind": "type_def", "span": span, "name": "T"})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _parse_go(self, source: str, filename: str) -> ParseResult:
        """Go解析器（简化版）"""
        result = ParseResult(language="go", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if "func " in stripped:
                result.nodes.append({"kind": "function_def", "span": span, "name": "func"})
            elif "type " in stripped:
                result.nodes.append({"kind": "type_def", "span": span, "name": "T"})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _parse_haskell(self, source: str, filename: str) -> ParseResult:
        """Haskell解析器（简化版）"""
        result = ParseResult(language="haskell", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if "data " in stripped or "type " in stripped:
                result.nodes.append({"kind": "type_def", "span": span, "name": "T"})
            elif "::" in stripped:
                result.nodes.append({"kind": "function_def", "span": span, "name": "func"})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _parse_c(self, source: str, filename: str) -> ParseResult:
        """C解析器（简化版）"""
        result = ParseResult(language="c", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if stripped.startswith("#include"):
                result.nodes.append({"kind": "import", "span": span})
            elif "int main" in stripped or "void " in stripped:
                result.nodes.append({"kind": "function_def", "span": span, "name": "main"})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result

    def _parse_relational(self, source: str, filename: str) -> ParseResult:
        """关系代数语言解析器（简化版）"""
        result = ParseResult(language="relational", raw_tree={}, standard_ast={}, nodes=[])
        lines = source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("%"):
                continue
            
            span = f"{i+1}:1-{i+1}:{len(line)}"
            if ":" in stripped:
                result.nodes.append({"kind": "rule", "span": span})
            elif stripped.startswith("INPUT") or stripped.startswith("OUTPUT"):
                result.nodes.append({"kind": "decl", "span": span})

        result.standard_ast = {"kind": "program", "nodes": result.nodes}
        return result
