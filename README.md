# dirtree

目录进，树出来。经典 `tree` 命令的 Python 实现：纯标准库、零依赖，
符号链接只显示不跟随，排序可预期。

## 安装

```bash
python3 -m dirtree <目录>
# 或直接运行
python3 dirtree.py <目录>
```

## 用法

```bash
dirtree ~/workspace/ai-forks/mdflow
dirtree . --depth 2                 # 只显示 2 层
dirtree . --dirs-only               # 只看目录
dirtree . --include "*.py"          # 只看 Python 文件（目录结构保留以便定位）
dirtree . --exclude "__pycache__" --exclude ".git"
dirtree . --sizes                   # 文件名后附带大小
dirtree . --json                    # 嵌套 JSON，方便脚本消费
dirtree . --no-dirs-first           # 不分目录/文件，统一自然排序
```

示例输出：

```
/home/hatch/workspace/ai-forks/mdflow
├── LICENSE
├── README.md
├── __pycache__
├── examples
│   └── hello.md
└── mdflow.py

2 个目录，5 个文件
```

- 目录默认排在文件前面，同组内按自然排序（忽略大小写，`file2` 排在
  `file10` 前面）。
- 符号链接显示为 `name -> target`，目录链接不递归进入（防循环）。
- 最后一个子项用 `└──`，其余用 `├──`，嵌套层级用 `│   ` 对齐。

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 正常 |
| 1 | 路径不是目录 |
| 2 | 参数错误（argparse） |

## 已知局限

- 只认本地文件系统，不跟随任何符号链接。
- `--sizes` 显示的是文件表观大小，不是磁盘块占用。
- 无权限的目录显示 `[无法读取: …]` 并继续，不中断。
- 排序是"目录优先 + 自然排序"的固定规则，不支持按大小/时间排序。
- 极大目录一次性输出到终端，建议配合 `--depth` 或 `--exclude` 使用。

## License

MIT，Copyright (c) 2026 ljiang9。见 [LICENSE](LICENSE)。
