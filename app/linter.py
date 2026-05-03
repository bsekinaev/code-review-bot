import logging
import os
import subprocess
import tempfile
import json
from typing import Optional

logger = logging.getLogger('uvicorn')

def run_ruff(file_content: str, filename: str = "file.py",
             ignore_rules: Optional[list[str]] = None,
             select_rules: Optional[list[str]] = None) -> list[dict]:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding="utf-8") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        cmd = ['ruff','check', '--output-format=json']
        if ignore_rules:
            cmd.append(f"--ignore={','.join(ignore_rules)}")
        if select_rules:
            cmd.append(f"--select={','.join(select_rules)}")
        cmd.append(tmp_path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return []
        else:
            try:
                problems = json.loads(result.stdout)
                return problems
            except json.decoder.JSONDecodeError:
                logger.error(f'Вывод Ruff не поддается разбору:{result.stdout}')
                return []

    finally:
        os.unlink(tmp_path)