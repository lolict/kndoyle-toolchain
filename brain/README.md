# 外置大脑 - 个人知识库 + 提问接口

你的所有对话/文档沉淀成一个可检索的外部记忆库。大脑自己记不住的东西，交给它存。

## 结构

```
brain/
  docs/       # 你的文档（.txt，标题第一行）
  build.py    # 重建索引：扫描 docs/ → 生成 kb.json
  ask.py      # 提问接口：倒排命中 + 三维坐标邻近 + 片段回显
  kb.json     # 索引数据（build.py 生成）
```

## 使用

首次构建：

```bash
python3 build.py
```

提问（单次）：

```bash
python3 ask.py "离线模型"
```

提问（交互模式）：

```bash
python3 ask.py
你> 我之前关于范畴论的对话在哪？
```

## 添加新记忆

把新的对话/文档（.txt，首行写标题）放进 `docs/`，重新跑一次：

```bash
cp 新文档.txt docs/
python3 build.py
```

## 检索原理

- **分词**：jieba 中文分词，建立倒排索引（词 → 文档 + 位置）
- **三维坐标**：每篇按标签向量落在 (领域, AI度, 落地性) 坐标空间
- **排序**：命中词数量 + 坐标距离加权，命中多的、坐标近的排前面
- **片段**：取命中的第一个位置前后各约 90 字，快速回忆上下文

## 依赖

```bash
pip install jieba
```

手机上（Termux）一样跑：装好 Termux 后 `pip install jieba` 即可。
