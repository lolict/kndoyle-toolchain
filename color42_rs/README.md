# color42_rs - 汉字本体编码系统 · Rust 零依赖实现

**你的编码系统，用系统语言自包含实现。** 不再长在别人语言的运行时上。
单二进制，零依赖，无运行时开销。

## 两个层面

### 1. 编码系统（color42 命令行）

42 进制三维编码，每字一数码、不替代代号：

```bash
./target/release/color42 list                 # 两套表
./target/release/color42 e 100 颜色 3         # 100 → 红黄赭
./target/release/color42 d 红黄赭             # 红黄赭 → 100
./target/release/color42 v 红                 # 红 = 0
./target/release/color42 p 缥 韵律            # (行3, 列1)
./target/release/color42 g 黟 韵律            # 光系·韵
```

### 2. 编程语言雏形（color42 run）

**汉字就是指令，汉字就是数码** —— 两个表天然区分：

- **数值 = 颜色表字**（无梯度，纯数码）
- **指令 = 韵律表字**（有梯度，字即"韵"意即动作）

指令集（操作码取自韵律表）：

| 指令 | 字 | 动作 |
|---|---|---|
| push | 妃 | 压入下一组 42 进制数值（3 颜色字） |
| dup | 粉 | 复制栈顶 |
| pop | 彤 | 弹出 |
| add | 赤 | 相加 |
| sub | 棕 | 相减 |
| mul | 绛 | 相乘 |
| div | 赭 | 整除 |
| print | 缃 | 打印栈顶（十进制） |
| printc | 金 | 打印栈顶对应汉字数码 |
| swap | 黄 | 交换栈顶两数 |
| halt | 褐 | 停机 |

运行：

```bash
./target/release/color42 run examples/add42.c42
# 输出: 142
```

## 设计要点

- **两表分工即语法**：颜色字只能是数值，韵律字只能是指令，歧义归零
- **规则即数据，不锁死**：指令规则在 `rules/vm.chain`（用汉字定义），
  新增指令只加一行，不动程序本体。你的规则是你的，随时可改可扩展
- **42 进制原生**：数值域 0..74087（三维），超出自动需多维度，天然分层
- **Rust 核心**：编译 3s、strip 后 351K、无运行时，可嵌入任意系统
- 示例见 `examples/`，测试见 `src/vm.rs`（cargo test，含自定义规则测试）

## 扩展你的规则

编辑 `rules/vm.chain` 自由扩展区，一行一条：

```text
# 指令 | 操作 | 参数数
缥 | print | 0
```

已支持的操作为内置语义（push/dup/pop/add/sub/mul/div/print/printc/swap/halt），
新的指令字可以映射到任意已支持操作，或后续扩展新操作。
