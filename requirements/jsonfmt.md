# 需求：JSON 格式化与验证工具

## 目标
写一个命令行工具 `jsonfmt.py`，接收 JSON 文件路径，格式化输出并做基础验证。

## 功能要求
1. 接收文件路径参数（`--file` 或位置参数）
2. 格式化输出（缩进 2 空格，中文不转义 Unicode）
3. 验证 JSON 语法合法性，非法时给出具体错误位置
4. 支持 `--check` 模式：只验证不输出，返回码 0/1
5. 支持 `--output` 指定输出文件，默认 stdout

## 接口定义
```python
def format_json(input_path: str, output_path: str = None) -> str
```

## 测试用例
| 输入 | 期望 |
|------|------|
| 合法紧凑 JSON | 格式化后正确缩进 |
| 含中文的 JSON | 中文原样保留，不转义为 \uXXXX |
| 语法错误 JSON | 报具体行列位置 |
| --check 合法 | 返回码 0，无输出 |
| --check 非法 | 返回码 1，stderr 报错 |

## 质量要求
- 类型注解
- 异常处理
- pytest 覆盖率
- 遵循 PEP8
