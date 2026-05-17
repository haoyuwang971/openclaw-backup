"""
JSON 格式化与验证工具

功能：
- 格式化 JSON 文件（2 空格缩进，中文不转义 Unicode）
- 验证 JSON 语法合法性，提供具体行列错误位置
- 支持 --check 模式（仅验证，返回 0/1）
- 支持 --output 指定输出文件（默认 stdout）
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


class JSONFormatError(Exception):
    """JSON 格式错误的自定义异常。"""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._fmt())

    def _fmt(self) -> str:
        if self.line > 0 and self.column > 0:
            return f"JSON 语法错误: 第 {self.line} 行, 第 {self.column} 列 — {self.message}"
        return f"JSON 语法错误: {self.message}"


def _parse_json_error(raw: str, err: json.JSONDecodeError) -> tuple[int, int]:
    """
    将 json.JSONDecodeError 的位置信息转换为行列号。

    Args:
        raw: 原始 JSON 文本。
        err: json.JSONDecodeError 异常对象。

    Returns:
        (line, column) 元组，1-based。
    """
    # json.JSONDecodeError 提供的 lineno 和 colno 在标准库中已经是 1-based
    # 但为了跨版本兼容，显式计算一次
    pos = err.pos
    line = 1
    column = 1
    for i, ch in enumerate(raw):
        if i >= pos:
            break
        if ch == "\n":
            line += 1
            column = 1
        else:
            column += 1
    return line, column


def _load_json(input_path: str) -> tuple[object, str]:
    """
    读取并解析 JSON 文件。

    Args:
        input_path: JSON 文件路径。

    Returns:
        (parsed_data, raw_text) 元组。

    Raises:
        JSONFormatError: JSON 语法错误时抛出，附带行列位置。
        FileNotFoundError: 文件不存在。
        PermissionError: 无权限读取文件。
    """
    path = Path(input_path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"文件不存在: {input_path}") from e
    except PermissionError as e:
        raise PermissionError(f"无权限读取文件: {input_path}") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        line, column = _parse_json_error(raw, e)
        raise JSONFormatError(str(e), line=line, column=column) from e

    return data, raw


def format_json(input_path: str, output_path: Optional[str] = None) -> str:
    """
    读取 JSON 文件，格式化后写入输出文件或返回格式化字符串。

    Args:
        input_path: 输入 JSON 文件路径。
        output_path: 输出文件路径。若为 None，则不写入文件。

    Returns:
        格式化后的 JSON 字符串。

    Raises:
        JSONFormatError: JSON 语法错误时抛出。
        FileNotFoundError: 输入文件不存在。
        PermissionError: 无权限读取/写入文件。
    """
    data, _ = _load_json(input_path)

    formatted = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
        sort_keys=False,
    )

    if output_path is not None:
        out = Path(output_path)
        try:
            out.write_text(formatted, encoding="utf-8")
        except PermissionError as e:
            raise PermissionError(f"无权限写入文件: {output_path}") from e

    return formatted


def check_json(input_path: str) -> bool:
    """
    仅验证 JSON 语法合法性，不输出格式化结果。

    Args:
        input_path: JSON 文件路径。

    Returns:
        True 表示合法，False 表示非法（错误信息已打印到 stderr）。
    """
    try:
        _load_json(input_path)
    except (JSONFormatError, FileNotFoundError, PermissionError) as e:
        print(str(e), file=sys.stderr)
        return False
    return True


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI 入口。

    Args:
        argv: 命令行参数列表。默认从 sys.argv 解析。

    Returns:
        进程退出码（0 成功，1 失败）。
    """
    parser = argparse.ArgumentParser(
        prog="jsonfmt",
        description="JSON 格式化与验证工具",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="输入 JSON 文件路径（也可通过 --file 指定）",
    )
    parser.add_argument(
        "--file", "-f",
        dest="file_arg",
        default=None,
        help="输入 JSON 文件路径",
    )
    parser.add_argument(
        "--output", "-o",
        dest="output",
        default=None,
        help="输出文件路径（默认 stdout）",
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="仅验证 JSON 语法，不输出格式化内容",
    )

    args = parser.parse_args(argv)

    # 确定输入路径：位置参数优先于 --file
    input_path: Optional[str] = args.path or args.file_arg
    if input_path is None:
        parser.error("必须提供输入文件路径")
        return 1  # pragma: no cover

    if args.check:
        ok = check_json(input_path)
        return 0 if ok else 1

    try:
        formatted = format_json(input_path, output_path=args.output)
    except (JSONFormatError, FileNotFoundError, PermissionError) as e:
        print(str(e), file=sys.stderr)
        return 1

    # 只有未指定 --output 时才打印到 stdout
    if args.output is None:
        print(formatted)

    return 0


if __name__ == "__main__":
    sys.exit(main())
