# cmdenv - 沙箱模拟指令环境

**为仓库提供完整指令环境**：协议/感知/角色/执行/时间/关系/进制 六类指令。
不依赖任何外部系统，自身就是一个"最小指令系统"。

## 核心原则

- **规则即数据**：指令定义在 `rules/cmd.chain`，格式 `指令|类别|参数数|行为`
- **缺什么补什么**：新增指令只加一行，程序本体不动
- **静态符号化执行**：沙箱模式，无需外部工具，模拟完整指令环境

## 六类指令

| 层 | 指令示例 | 功能 |
|---|---|---|
| 协议 | gttx / gkhtfqndl / gkhfkndl / hftqmll / gkhtml | 通信·寻址·标记 |
| 感知 | gkndl / fqmy / hfuyair / hinynir / smrrll | 感知→驱动转化 |
| 角色 | gtxone / kndoyle / maolilan / hieyair | 中心/判定/镜像/还原 |
| 执行 | run / ping / list / state | 命令处理·状态 |
| 时间 | tclgs / juan / time | 时间编码生命周期治理 |
| 关系 | gcd / lcm / mirror / add / mul | 公约数·公倍数·镜像对偶 |
| 进制 | qe / qd / c42 / y42 / kan / trans | 42进制·音韵·谱系·跨感官 |

## 使用

```bash
# 列出全部指令
cmdenv list

# 42进制编解码
cmdenv qe 42        # 42 → 妃粉妃
cmdenv qd 黟黟黟     # 黟黟黟 → 74087

# 关系算子
cmdenv gcd 42 60    # 公约数(中心男人) = 6
cmdenv lcm 42 2760  # 公倍数(边界女人) = 19320
cmdenv mirror 42 14 # 14 ↔ 27 (对称轴 20.5)

# 系统状态
cmdenv state 合一爱人

# 时间功法
cmdenv tclgs fold 编码   # 折叠 → 回归中心一
cmdenv juan 工藤新一      # 相位颠倒 → 空间(毛利兰)

# 执行管线 (概念演示)
cmdenv run 智能索引 100
```

## 与你的概念对应

- **沙箱模拟**：在受限环境（Termux/无网沙箱）中，不需要下载别人的操作系统，
  用自己预加载的底层编码系统模拟上层工具
- **指令环境**：系统需要什么指令，就在 `rules/cmd.chain` 补什么指令
- **规则即数据**：与 vm.chain / spectrum.chain / sense.chain 同一哲学
- **回归中心一**：所有执行结果最终以"回归工藤新一公约数中心"为目的

## 规则文件

`rules/cmd.chain` —— 全部以人类语言书写，可自由扩展。
未来新增生态（如天干地支/生肖/节气）只需在规则表加行。
