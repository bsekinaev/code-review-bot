from app.linter import run_ruff

def test_clean_code():
    code = 'print("hello")\n'
    problems = run_ruff(code)
    assert len(problems) == 0

def test_unused_import():
    code = 'import os\nprint("hello")\n'
    problems = run_ruff(code)
    assert len(problems) > 0
    assert any ('os' in p.get("message",'') for p in problems)

def test_unused_import_ignored():
    code = 'import os\nprint("hello")\n'
    problems = run_ruff(code, ignore_rules=['F401'])
    assert len(problems) == 0

def test_select_rules():
    code = 'import os\nimport sys\nprint("hello")\n'
    problems = run_ruff(code, select_rules=["E501"])
    assert len(problems) == 0




