"""Minimal test runner for environments without pytest: python -m intraday.selftest"""
import importlib
import sys
import traceback

mod = importlib.import_module("tests.test_intraday")
fails = 0
names = [n for n in dir(mod) if n.startswith("test_")]
for name in names:
    try:
        getattr(mod, name)()
        print(f"PASS {name}")
    except Exception:
        fails += 1
        print(f"FAIL {name}\n{traceback.format_exc()}")
print(f"\n{len(names) - fails} passed, {fails} failed")
sys.exit(1 if fails else 0)
