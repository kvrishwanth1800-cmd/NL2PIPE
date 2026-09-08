from nl2pipe.generate import strip_code_fences


def test_strip_plain_code_unchanged():
    code = "import dlt\nprint('hi')\n"
    assert strip_code_fences(code) == code


def test_strip_python_fence():
    fenced = "```python\nimport dlt\nprint('hi')\n```"
    assert strip_code_fences(fenced) == "import dlt\nprint('hi')\n"


def test_strip_bare_fence():
    fenced = "```\nx = 1\n```"
    assert strip_code_fences(fenced) == "x = 1\n"


def test_trailing_whitespace_trimmed_and_newline_added():
    assert strip_code_fences("x = 1   ").endswith("\n")
