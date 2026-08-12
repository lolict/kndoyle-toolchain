// vm.rs - 汉字本体编程语言 v0.1 · 栈式虚拟机
//
// 设计：
//   数值 = 颜色表字（表1 无梯度，纯数码）
//   指令 = 韵律表字（表2 有梯度，字即"韵"意即动作）
//   42 进制：连续 3 个颜色字 = 一个数值数码（0..74087）
//
// 指令集（操作码取自韵律表）：
//   妃 push   压入下一组 42 进制数值
//   粉 dup    复制栈顶
//   彤 pop    弹出
//   赤 add    栈顶两数相加
//   棕 sub    栈顶两数相减
//   绛 mul    栈顶两数相乘
//   赭 div    栈顶两数整除
//   缃 print  打印栈顶数值(十进制)
//   金 printc 打印栈顶数值对应的汉字数码
//   黄 swap   交换栈顶两数
//   褐 halt   停机

// 韵律表（指令码源）
const OP_FLAT: &str = "妃粉彤赤棕绛赭缃金黄褐黧乌黑缥翠绿青苍黛玄素银蓝紫靛绀黯玉琅晶璃珀瑙璧曦辉霓旖靡暝黟";

// 颜色表（数值数码源）
const NUM_FLAT: &str = "红橙黄绿青蓝紫褐棕黑靛粉彩白朱绛赭丹彤缃黛翠碧缥素银金灰玉琅晶璃珀瑙璧曦辉霓旖靡暝黟";

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

pub fn parse_op(ch: char) -> Option<Op> {
    let idx = OP_FLAT.chars().position(|c| c == ch)?;
    Some(match idx {
        0 => Op::Push(0), // 妃 占位，实参由解析器读后续数值
        1 => Op::Dup,
        2 => Op::Pop,
        3 => Op::Add,
        4 => Op::Sub,
        5 => Op::Mul,
        6 => Op::Div,
        7 => Op::Print,
        8 => Op::PrintC,
        9 => Op::Swap,
        10 => Op::Halt,
        _ => return None,
    })
}

// 解析源程序：token 流 → 指令序列
// 源程序由韵律字(指令)与颜色字(数值)组成，遇 push(妃) 读后续 3 个颜色字为数值
pub fn parse(src: &str) -> Result<Vec<Op>, String> {
    let chars: Vec<char> = src.chars().collect();
    let mut ops = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '#' {
            // 注释：跳过到行尾
            while i < chars.len() && chars[i] != '\n' {
                i += 1;
            }
            continue;
        }
        if c == '妃' {
            // push：读后续 3 个颜色字
            if i + 3 >= chars.len() {
                return Err("push(妃) 后缺数值（需 3 个颜色字）".into());
            }
            let numstr: String = chars[i + 1..i + 4].iter().collect();
            let mut v: u64 = 0;
            for nc in numstr.chars() {
                let idx = NUM_FLAT.chars().position(|x| x == nc)
                    .ok_or(format!("数值字 [{}] 不在颜色表", nc))?;
                v = v * 42 + idx as u64;
            }
            ops.push(Op::Push(v));
            i += 4;
        } else if let Some(op) = parse_op(c) {
            if let Op::Push(_) = op {
                return Err("内部错误".into());
            }
            ops.push(op);
            i += 1;
        } else if OP_FLAT.contains(c) {
            return Err(format!("指令字 [{}] 未定义操作码", c));
        } else if c.is_whitespace() {
            i += 1;
        } else {
            return Err(format!("未知字符 [{}]：须为韵律表指令或颜色表数值", c));
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

    #[test]
    fn test_add() {
        // 妃红红橙 妃红红红 赤 缃 褐   => push 1, push 0, add, print => 1
        let ops = parse("妃红红橙妃红红红赤缃褐").unwrap();
        run(&ops).unwrap();
    }

    #[test]
    fn test_42() {
        // push 41, printc => 黟
        let ops = parse("妃红红黟金褐").unwrap();
        run(&ops).unwrap();
    }

    #[test]
    fn test_sub() {
        // push 100(红黄赭), push 42(红橙红), sub, print => 58
        let ops = parse("妃红黄赭妃红橙红棕缃褐").unwrap();
        run(&ops).unwrap();
    }
}
