// vm.rs - 汉字本体编程语言 v0.2 · 栈式虚拟机 · 规则即数据
//
// 规则从 rules/vm.chain 加载 (不是硬编码) —— 新增/修改指令只改规则文件, 不动程序本体.
//
// 设计：
//   数值 = 颜色表字（表1 无梯度，纯数码）
//   指令 = 韵律表字（表2 有梯度，字即"韵"意即动作）
//   42 进制：连续 3 个颜色字 = 一个数值数码（0..74087）
//
// 规则格式: 指令 | 操作 | 参数数
//   妃 | push | 3    压入下一组 42 进制数值(3个颜色字)
//   粉 | dup  | 0    复制栈顶
//   彤 | pop  | 0    弹出
//   赤 | add  | 0    栈顶两数相加
//   棕 | sub  | 0    栈顶两数相减
//   绛 | mul  | 0    栈顶两数相乘
//   赭 | div  | 0    栈顶两数整除
//   缃 | print| 0    打印栈顶数值(十进制)
//   金 | printc| 0   打印栈顶数值对应汉字数码
//   黄 | swap | 0    交换栈顶两数
//   褐 | halt | 0    停机

use std::collections::HashMap;
use std::fs;

// 颜色表（数值数码源）
const NUM_FLAT: &str = "红橙黄绿青蓝紫褐棕黑靛粉彩白朱绛赭丹彤缃黛翠碧缥素银金灰玉琅晶璃珀瑙璧曦辉霓旖靡暝黟";

// 指令操作码枚举
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Op {
    Push(u64),
    Dup,
    Pop,
    Add,
    Sub,
    Mul,
    Div,
    Print,
    PrintC,
    Swap,
    Halt,
}

pub struct Rule {
    pub op: String,
    pub nargs: usize,
}

// 加载规则表: 指令字 → (操作, 参数数)
pub fn load_rules(path: &str) -> Result<HashMap<char, Rule>, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("规则表读取失败: {}", e))?;
    let mut rules = HashMap::new();
    for (i, line) in content.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.len() < 2 {
            return Err(format!("规则表第 {} 行格式错误: {}", i + 1, line));
        }
        let ch = parts[0].chars().next().ok_or(format!("第 {} 行无指令字", i + 1))?;
        let op = parts[1].to_string();
        let nargs = parts.get(2).and_then(|v| v.parse().ok()).unwrap_or(0);
        rules.insert(ch, Rule { op, nargs });
    }
    if rules.is_empty() {
        return Err("规则表为空".into());
    }
    Ok(rules)
}

// 解析源程序：token 流 → 指令序列
// push 指令后读 nargs 个颜色字为数值
pub fn parse(src: &str, rules: &HashMap<char, Rule>) -> Result<Vec<Op>, String> {
    let chars: Vec<char> = src.chars().collect();
    let mut ops = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '#' {
            while i < chars.len() && chars[i] != '\n' {
                i += 1;
            }
            continue;
        }
        if let Some(rule) = rules.get(&c) {
            match rule.op.as_str() {
                "push" => {
                    if i + rule.nargs >= chars.len() {
                        return Err(format!("push({}) 后缺数值（需 {} 个颜色字）", c, rule.nargs));
                    }
                    let numstr: String = chars[i + 1..i + 1 + rule.nargs].iter().collect();
                    let mut v: u64 = 0;
                    for nc in numstr.chars() {
                        let idx = NUM_FLAT.chars().position(|x| x == nc)
                            .ok_or(format!("数值字 [{}] 不在颜色表", nc))?;
                        v = v * 42 + idx as u64;
                    }
                    ops.push(Op::Push(v));
                    i += 1 + rule.nargs;
                }
                "dup" => { ops.push(Op::Dup); i += 1; }
                "pop" => { ops.push(Op::Pop); i += 1; }
                "add" => { ops.push(Op::Add); i += 1; }
                "sub" => { ops.push(Op::Sub); i += 1; }
                "mul" => { ops.push(Op::Mul); i += 1; }
                "div" => { ops.push(Op::Div); i += 1; }
                "print" => { ops.push(Op::Print); i += 1; }
                "printc" => { ops.push(Op::PrintC); i += 1; }
                "swap" => { ops.push(Op::Swap); i += 1; }
                "halt" => { ops.push(Op::Halt); i += 1; }
                other => return Err(format!("未定义操作 [{}] (指令 {})", other, c)),
            }
        } else if c.is_whitespace() {
            i += 1;
        } else if NUM_FLAT.contains(c) {
            return Err(format!("数值字 [{}] 未跟在 push 指令后", c));
        } else {
            return Err(format!("未知字 [{}]: 未注册进规则表", c));
        }
    }
    Ok(ops)
}

// 执行指令序列
pub fn run(ops: &[Op]) -> Result<(), String> {
    let mut stack: Vec<u64> = Vec::new();
    for op in ops {
        match op {
            Op::Push(v) => stack.push(*v),
            Op::Dup => {
                let t = *stack.last().ok_or("栈空: dup")?;
                stack.push(t);
            }
            Op::Pop => {
                stack.pop().ok_or("栈空: pop")?;
            }
            Op::Add => {
                let b = stack.pop().ok_or("栈空: add")?;
                let a = stack.pop().ok_or("栈空: add")?;
                stack.push(a + b);
            }
            Op::Sub => {
                let b = stack.pop().ok_or("栈空: sub")?;
                let a = stack.pop().ok_or("栈空: sub")?;
                stack.push(a.wrapping_sub(b));
            }
            Op::Mul => {
                let b = stack.pop().ok_or("栈空: mul")?;
                let a = stack.pop().ok_or("栈空: mul")?;
                stack.push(a * b);
            }
            Op::Div => {
                let b = stack.pop().ok_or("栈空: div")?;
                let a = stack.pop().ok_or("栈空: div")?;
                if b == 0 {
                    return Err("除零错误".into());
                }
                stack.push(a / b);
            }
            Op::Print => {
                let t = *stack.last().ok_or("栈空: print")?;
                println!("{}", t);
            }
            Op::PrintC => {
                let t = *stack.last().ok_or("栈空: printc")?;
                let c = NUM_FLAT.chars().nth(t as usize)
                    .ok_or(format!("值 {} 超出颜色表 0-41", t))?;
                println!("{}", c);
            }
            Op::Swap => {
                if stack.len() < 2 {
                    return Err("栈不足: swap".into());
                }
                let n = stack.len();
                stack.swap(n - 1, n - 2);
            }
            Op::Halt => break,
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_rules() -> HashMap<char, Rule> {
        load_rules("rules/vm.chain").unwrap()
    }

    #[test]
    fn test_add() {
        let rules = test_rules();
        // push 1, push 0, add, print => 1
        let ops = parse("妃红红橙妃红红红赤缃褐", &rules).unwrap();
        run(&ops).unwrap();
    }

    #[test]
    fn test_42() {
        let rules = test_rules();
        // push 41, printc => 黟
        let ops = parse("妃红红黟金褐", &rules).unwrap();
        run(&ops).unwrap();
    }

    #[test]
    fn test_sub() {
        let rules = test_rules();
        // push 100, push 42, sub, print => 58
        let ops = parse("妃红黄赭妃红橙红棕缃褐", &rules).unwrap();
        run(&ops).unwrap();
    }

    #[test]
    fn test_custom_rule() {
        let rules = test_rules();
        // 缥 是自由扩展区加的 print 别名: push 42, 缥 => 42
        let ops = parse("妃红橙红缥褐", &rules).unwrap();
        run(&ops).unwrap();
    }
}
