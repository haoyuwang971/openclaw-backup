"""
pytest 测试套件 — jsonfmt

覆盖：
- 合法紧凑 JSON 格式化
- 中文不转义
- 语法错误行列位置
- --check 模式（合法/非法）
- 文件不存在 / 无权限
- 接口函数 format_json
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jsonfmt import JSONFormatError, check_json, format_json, main


@pytest.fixture
def tmp_json(tmp_path: Path) -> Path:
    """在临时目录中提供 JSON 文件工厂。"""
    def _make(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p
    return tmp_path  # 实际通过 tmp_path 直接操作即可，这里保留签名兼容


class TestFormatJson:
    """测试 format_json 核心函数。"""

    def test_compact_json_formatted(self, tmp_path: Path) -> None:
        """合法紧凑 JSON 应被正确格式化（2 空格缩进）。"""
        inp = tmp_path / "compact.json"
        inp.write_text('{"a":1,"b":[2,3]}', encoding="utf-8")
        result = format_json(str(inp))
        expected = json.dumps({"a": 1, "b": [2, 3]}, ensure_ascii=False, indent=2)
        assert result == expected

    def test_chinese_preserved(self, tmp_path: Path) -> None:
        """中文应原样保留，不转义为 \\uXXXX。"""
        inp = tmp_path / "chinese.json"
        inp.write_text('{"msg":"你好，世界"}', encoding="utf-8")
        result = format_json(str(inp))
        assert "你好，世界" in result
        assert "\\u" not in result

    def test_output_file_written(self, tmp_path: Path) -> None:
        """指定 output_path 时应写入文件。"""
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text('{"x":1}', encoding="utf-8")
        result = format_json(str(inp), output_path=str(out))
        assert out.exists()
        assert out.read_text(encoding="utf-8") == result

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """非法 JSON 应抛出 JSONFormatError 并带行列信息。"""
        inp = tmp_path / "bad.json"
        # 在第 2 行第 9 列（1-based）附近缺少逗号
        raw = '{\n  "a": 1\n  "b": 2\n}'
        inp.write_text(raw, encoding="utf-8")
        with pytest.raises(JSONFormatError) as exc_info:
            format_json(str(inp))
        err = exc_info.value
        assert err.line > 0
        assert err.column > 0
        assert "JSON 语法错误" in str(err)

    def test_file_not_found(self) -> None:
        """输入文件不存在时应抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            format_json("/nonexistent/path/file.json")

    def test_permission_error_read(self, tmp_path: Path) -> None:
        """无权限读取时应抛出 PermissionError。"""
        # 以 root 运行时 chmod 0o000 仍可读，跳过
        if os.getuid() == 0:
            pytest.skip("以 root 运行时无法模拟文件读取权限错误")
        inp = tmp_path / "noread.json"
        inp.write_text('{}', encoding="utf-8")
        os.chmod(str(inp), 0o000)
        try:
            with pytest.raises(PermissionError):
                format_json(str(inp))
        finally:
            os.chmod(str(inp), 0o644)

    def test_permission_error_write(self, tmp_path: Path) -> None:
        """无权限写入时应抛出 PermissionError。"""
        # 以 root 运行时 chmod 0o000 仍可写，跳过
        if os.getuid() == 0:
            pytest.skip("以 root 运行时无法模拟文件写入权限错误")
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text('{}', encoding="utf-8")
        out.write_text("", encoding="utf-8")
        os.chmod(str(out), 0o000)
        try:
            with pytest.raises(PermissionError):
                format_json(str(inp), output_path=str(out))
        finally:
            os.chmod(str(out), 0o644)


class TestCheckJson:
    """测试 check_json 验证函数。"""

    def test_valid_returns_true(self, tmp_path: Path) -> None:
        """合法 JSON 返回 True，stderr 无输出。"""
        inp = tmp_path / "ok.json"
        inp.write_text('{"a":1}', encoding="utf-8")
        assert check_json(str(inp)) is True

    def test_invalid_returns_false(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """非法 JSON 返回 False，stderr 有错误信息。"""
        inp = tmp_path / "bad.json"
        inp.write_text('{"a":}', encoding="utf-8")
        assert check_json(str(inp)) is False
        captured = capsys.readouterr()
        assert "JSON 语法错误" in captured.err


class TestCLI:
    """测试命令行入口 main()。"""

    def test_cli_format_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """未指定 --output 时格式化结果输出到 stdout。"""
        inp = tmp_path / "in.json"
        inp.write_text('{"b":2,"a":1}', encoding="utf-8")
        rc = main([str(inp)])
        assert rc == 0
        captured = capsys.readouterr()
        expected = json.dumps({"b": 2, "a": 1}, ensure_ascii=False, indent=2)
        assert captured.out.strip() == expected

    def test_cli_output_file(self, tmp_path: Path) -> None:
        """指定 --output 时写入文件，stdout 无输出。"""
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text('{"x":1}', encoding="utf-8")
        rc = main([str(inp), "--output", str(out)])
        assert rc == 0
        assert out.exists()
        expected = json.dumps({"x": 1}, ensure_ascii=False, indent=2)
        assert out.read_text(encoding="utf-8") == expected

    def test_cli_check_valid(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """--check 合法 JSON：返回 0，stdout/stderr 无输出。"""
        inp = tmp_path / "ok.json"
        inp.write_text('[]', encoding="utf-8")
        rc = main([str(inp), "--check"])
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_cli_check_invalid(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """--check 非法 JSON：返回 1，stderr 报错。"""
        inp = tmp_path / "bad.json"
        inp.write_text('{"a":}', encoding="utf-8")
        rc = main([str(inp), "--check"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "JSON 语法错误" in captured.err

    def test_cli_file_flag(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """使用 --file 标志应正常工作。"""
        inp = tmp_path / "in.json"
        inp.write_text('{"flag":true}', encoding="utf-8")
        rc = main(["--file", str(inp)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "\"flag\": true" in captured.out

    def test_cli_missing_path(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """未提供文件路径时应以非零退出码退出（argparse 处理）。"""
        # argparse 在缺少必要参数时调用 sys.exit(2)
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_cli_invalid_prints_stderr(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """格式化模式遇到非法 JSON 应打印到 stderr 并返回 1。"""
        inp = tmp_path / "bad.json"
        inp.write_text("not json", encoding="utf-8")
        rc = main([str(inp)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "JSON 语法错误" in captured.err
