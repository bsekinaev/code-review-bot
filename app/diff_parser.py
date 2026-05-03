import re

def parse_diff_ranges(patch: str) -> list[tuple[int, int]]:
    if not patch:
        return []
    lines = patch.split('\n')
    ranges = []
    current_start = None
    current_line = 0
    for line in lines:
        match = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
        if match:
            if current_start is not None:
                ranges.append((current_start, current_line - 1))
            new_start = int(match.group(1))
            new_count = int(match.group(2)) if match.group(2) else 1
            current_start = new_start
            current_line = new_start
        elif line.startswith('+') or (line.startswith(' ') and not line.startswith('-')):
            if current_start is not None:
                current_line += 1
    if current_start is not None:
        ranges.append((current_start, current_line - 1))
    return ranges