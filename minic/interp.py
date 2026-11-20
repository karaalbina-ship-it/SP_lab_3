import re
import sys

from minic import MiniCError


def wrap(x):
    return (x + 2**31) % 2**32 - 2**31


def c_div(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def c_mod(a, b):
    return a - b * c_div(a, b)


BINARY = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": c_div,
    "%": c_mod,
    "<": lambda a, b: int(a < b),
    ">": lambda a, b: int(a > b),
    "<=": lambda a, b: int(a <= b),
    ">=": lambda a, b: int(a >= b),
    "==": lambda a, b: int(a == b),
    "!=": lambda a, b: int(a != b),
}

FORMAT = re.compile(r"%(-?\d*)([dcs%])")


def cformat(fmt, args, line):
    args = list(args)

    def repl(m):
        width, conv = m.group(1), m.group(2)
        if conv == "%":
            return "%"
        if not args:
            raise MiniCError(f"line {line}: error: printf: not enough arguments")
        v = args.pop(0)
        s = v if conv == "s" else chr(v & 0xFF) if conv == "c" else str(v)
        if not width:
            return s
        w = int(width)
        return s.ljust(-w) if w < 0 else s.rjust(w)

    return FORMAT.sub(repl, fmt)


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self, program, out=sys.stdout):
        self.out = out
        self.funcs = {}
        self.globals = {}
        self.scopes = []
        for item in program.children:
            if item.kind == "Func":
                if item.value in self.funcs:
                    raise MiniCError(f"line {item.line}: error: function '{item.value}' redefined")
                self.funcs[item.value] = item
            else:
                for d in item.children:
                    self.declare(d, self.globals)

    def error(self, node, msg):
        raise MiniCError(f"line {node.line}: error: {msg}")

    def run(self):
        if "main" not in self.funcs:
            raise MiniCError("error: no function 'main'")
        sys.setrecursionlimit(20000)
        return self.call(self.funcs["main"], [], self.funcs["main"])

    def declare(self, node, scope):
        if node.type == "void":
            self.error(node, f"variable '{node.value}' declared void")
        if node.value in scope:
            self.error(node, f"'{node.value}' redeclared")
        if node.kind == "Array":
            size = node.children[0].value
            init = [self.eval(e) for e in node.children[1:]]
            if size <= 0 or len(init) > size:
                self.error(node, f"bad size of array '{node.value}'")
            scope[node.value] = init + [0] * (size - len(init))
        else:
            scope[node.value] = self.eval(node.children[0]) if node.children else 0

    def scope_of(self, node):
        for scope in reversed(self.scopes):
            if node.value in scope:
                return scope
        if node.value in self.globals:
            return self.globals
        self.error(node, f"'{node.value}' undeclared")

    def scalar(self, node):
        scope = self.scope_of(node)
        if isinstance(scope[node.value], list):
            self.error(node, f"'{node.value}' is an array")
        return scope, node.value

    def element(self, node):
        arr = self.scope_of(node)[node.value]
        if not isinstance(arr, list):
            self.error(node, f"'{node.value}' is not an array")
        i = self.eval(node.children[0])
        if not 0 <= i < len(arr):
            self.error(node, f"index {i} out of bounds of '{node.value}[{len(arr)}]'")
        return arr, i

    def place(self, node):
        return self.scalar(node) if node.kind == "Name" else self.element(node)

    def call(self, func, args, node):
        params = func.children[0].children
        if len(args) != len(params):
            self.error(node, f"'{func.value}' expects {len(params)} arguments, got {len(args)}")
        saved = self.scopes
        self.scopes = [{p.value: a for p, a in zip(params, args)}]
        try:
            self.exec(func.children[1])
        except ReturnSignal as r:
            return r.value
        except (BreakSignal, ContinueSignal) as jump:
            node = jump.args[0]
            self.error(node, f"'{node.kind.lower()}' outside a loop")
        finally:
            self.scopes = saved
        return 0

    def exec(self, node):
        k = node.kind
        if k == "Block":
            self.scopes.append({})
            try:
                for s in node.children:
                    self.exec(s)
            finally:
                self.scopes.pop()
        elif k == "Decl":
            for d in node.children:
                self.declare(d, self.scopes[-1])
        elif k == "ExprStmt":
            self.eval(node.children[0])
        elif k == "Empty":
            pass
        elif k == "If":
            if self.eval(node.children[0]):
                self.exec(node.children[1])
            elif len(node.children) == 3:
                self.exec(node.children[2])
        elif k == "While":
            cond, body = node.children
            while self.eval(cond):
                if self.loop_body(body):
                    break
        elif k == "DoWhile":
            body, cond = node.children
            while True:
                if self.loop_body(body):
                    break
                if not self.eval(cond):
                    break
        elif k == "For":
            init, cond, step, body = node.children
            self.scopes.append({})
            try:
                self.exec(init) if init.kind == "Decl" else self.eval(init)
                while cond.kind == "Empty" or self.eval(cond):
                    if self.loop_body(body):
                        break
                    self.eval(step)
            finally:
                self.scopes.pop()
        elif k == "Return":
            raise ReturnSignal(self.eval(node.children[0]) if node.children else 0)
        elif k == "Break":
            raise BreakSignal(node)
        elif k == "Continue":
            raise ContinueSignal(node)
        else:
            self.error(node, f"unknown statement {k}")

    def loop_body(self, body):
        try:
            self.exec(body)
        except BreakSignal:
            return True
        except ContinueSignal:
            pass
        return False

    def eval(self, node):
        k = node.kind
        if k == "Empty":
            return 0
        if k == "Num":
            return node.value
        if k == "Str":
            return node.value
        if k == "Name":
            scope, name = self.scalar(node)
            return scope[name]
        if k == "Index":
            arr, i = self.element(node)
            return arr[i]
        if k == "Bin":
            a, b = self.eval(node.children[0]), self.eval(node.children[1])
            if node.value in "/%" and b == 0:
                self.error(node, "division by zero")
            return wrap(BINARY[node.value](a, b))
        if k == "Logic":
            a = self.eval(node.children[0])
            if node.value == "&&":
                return int(bool(a) and bool(self.eval(node.children[1])))
            return int(bool(a) or bool(self.eval(node.children[1])))
        if k == "Unary":
            v = self.eval(node.children[0])
            return wrap(-v) if node.value == "-" else int(not v)
        if k == "Cond":
            c = self.eval(node.children[0])
            return self.eval(node.children[1] if c else node.children[2])
        if k == "Assign":
            target, rhs = node.children
            value = self.eval(rhs)
            box, key = self.place(target)
            if node.value != "=":
                op = node.value[0]
                if op in "/%" and value == 0:
                    self.error(node, "division by zero")
                value = wrap(BINARY[op](box[key], value))
            box[key] = value
            return value
        if k in ("PreInc", "PostInc"):
            box, key = self.place(node.children[0])
            old = box[key]
            box[key] = wrap(old + (1 if node.value == "++" else -1))
            return box[key] if k == "PreInc" else old
        if k == "Call":
            return self.builtin_or_call(node)
        self.error(node, f"unknown expression {k}")

    def builtin_or_call(self, node):
        args = [self.eval(a) for a in node.children]
        if node.value == "printf":
            if not args or not isinstance(args[0], str):
                self.error(node, "printf needs a format string")
            text = cformat(args[0], args[1:], node.line)
            self.out.write(text)
            return len(text)
        if node.value == "putchar":
            if len(args) != 1:
                self.error(node, "putchar expects 1 argument")
            self.out.write(chr(args[0] & 0xFF))
            return args[0]
        if node.value not in self.funcs:
            self.error(node, f"function '{node.value}' undeclared")
        if any(isinstance(a, str) for a in args):
            self.error(node, "string literal allowed only in printf")
        return self.call(self.funcs[node.value], args, node)
