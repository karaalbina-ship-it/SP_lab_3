import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_ERRORS = {
    "syntax.c": "line 3: syntax error near '{'",
    "undeclared.c": "line 3: error: 'b' undeclared",
    "args.c": "line 6: error: 'add' expects 2 arguments, got 1",
    "break.c": "line 3: error: 'break' outside a loop",
    "bounds.c": "line 4: error: index 5 out of bounds",
    "divzero.c": "line 3: error: division by zero",
}


def minic(mode, path):
    r = subprocess.run(
        [sys.executable, "-m", "minic", mode, str(path)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    return r.returncode, r.stdout.replace("\r\n", "\n"), r.stderr.strip()


def main():
    failed = 0
    for src in sorted((ROOT / "examples").glob("*.c")):
        want = src.with_suffix(".out").read_text(encoding="utf-8").replace("\r\n", "\n")
        for mode in ("run", "vm"):
            rc, out, err = minic(mode, src)
            ok = rc == 0 and out == want
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {mode:<3} {src.name}" + ("" if ok else f"  {err}"))
    for src in sorted((ROOT / "tests" / "errors").glob("*.c")):
        for mode in ("run", "vm"):
            rc, out, err = minic(mode, src)
            ok = rc != 0 and err.startswith(EXPECTED_ERRORS[src.name])
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {mode:<3} errors/{src.name}: {err}")
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


sys.exit(main())
