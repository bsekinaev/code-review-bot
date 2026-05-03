from app.diff_parser import parse_diff_ranges

def test_simple_patch():
    patch = """@@ -1,3 +1,4 @@
 old line
+new line
 context
+another new line
"""
    ranges = parse_diff_ranges(patch)
    assert ranges == [(1, 4)]

def test_multiple_hunks():
    patch = """@@ -10,7 +10,6 @@
 unchanged
-changed
 another unchanged
@@ -20,5 +20,7 @@
 start
+added
 end
"""
    ranges = parse_diff_ranges(patch)
    assert len(ranges) == 2
    assert ranges[0] == (10, 11)
    assert ranges[1] == (20, 22)

def test_empty_patch():
    assert parse_diff_ranges("") == []
    assert parse_diff_ranges(None) == []