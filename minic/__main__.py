import argparse
import json
import subprocess
import sys
from pathlib import Path

from minic import MiniCError
from minic.ast import print_tree, to_dict
from minic.codegen import compile_program, listing
from minic.interp import Interpreter
from minic.parser import make_parser, parse

ROOT = Path(__file__).resolve().parent.parent
VM_JS = ROOT / "vm" / "vm.js"
TEMPLATE = ROOT / "viz" / "template.html"


def run_vm(prog):
    result = subprocess.run(
        ["node", str(VM_JS)], input=json.dumps(prog), capture_output=True, text=True, encoding="utf-8"
    )
    sys.stdout.write(result.stdout)
    if result.returncode:
        raise MiniCError(result.stderr.strip())


def make_html(path, source, tree, prog, out):
    data = {"name": Path(path).name, "source": source, "ast": to_dict(tree), "program": prog}
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*VM*/", VM_JS.read_text(encoding="utf-8"))
    page = page.replace("/*DATA*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = Path(out) if out else ROOT / "out" / (Path(path).stem + ".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    ap = argparse.ArgumentParser(prog="python -m minic")
    ap.add_argument("mode", choices=["tree", "json", "run", "bc", "vm", "html", "grammar"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("out", nargs="?")
    args = ap.parse_args()
    if args.mode == "grammar":
        make_parser(debug=True, outdir=args.file or ".")
        print(Path(args.file or ".") / "parser.out")
        return 0
    if not args.file:
        ap.error("file is required")
    source = Path(args.file).read_text(encoding="utf-8")
    try:
        tree = parse(source)
        if args.mode == "tree":
            print(print_tree(tree))
        elif args.mode == "json":
            print(json.dumps(to_dict(tree), ensure_ascii=False, indent=1))
        elif args.mode == "run":
            compile_program(tree)
            Interpreter(tree).run()
        else:
            prog = compile_program(tree)
            if args.mode == "bc":
                print(listing(prog))
            elif args.mode == "vm":
                run_vm(prog)
            else:
                make_html(args.file, source, tree, prog, args.out)
    except MiniCError as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
        return 1
    return 0


sys.exit(main())
