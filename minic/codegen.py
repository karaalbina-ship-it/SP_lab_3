from minic import MiniCError
from minic.interp import BINARY, wrap

BIN_OPS = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
    "==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
}

JUMPS = {"JMP", "JZ", "JNZ"}


def fold(node):
    if node.kind == "Num":
        return node.value
    if node.kind == "Unary":
        v = fold(node.children[0])
        if v is not None:
            return wrap(-v) if node.value == "-" else int(not v)
    if node.kind == "Bin":
        a, b = fold(node.children[0]), fold(node.children[1])
        if a is not None and b is not None and not (node.value in "/%" and b == 0):
            return wrap(BINARY[node.value](a, b))
    return None


class Codegen:
    def __init__(self, program):
        self.code = []
        self.strings = []
        self.labels = {}
        self.globals = {}
        self.funcs = {}
        self.scopes = None
        self.loops = []
        self.node = program
        for item in program.children:
            if item.kind == "Func":
                if item.value in self.funcs or item.value in ("printf", "putchar"):
                    self.error(item, f"function '{item.value}' redefined")
                self.funcs[item.value] = {"node": item, "params": len(item.children[0].children)}
        if "main" not in self.funcs:
            raise MiniCError("error: no function 'main'")
        for item in program.children:
            if item.kind == "Decl":
                for d in item.children:
                    self.declare(d, self.globals, "G")
        self.emit("CALL", "main", 0)
        self.emit("POP")
        self.emit("HALT")
        for item in program.children:
            if item.kind == "Func":
                self.function(item)
        self.resolve()

    def error(self, node, msg):
        raise MiniCError(f"line {node.line}: error: {msg}")

    def emit(self, op, arg=None, arg2=None):
        self.code.append({"op": op, "arg": arg, "arg2": arg2, "line": self.node.line, "node": self.node.id})

    def label(self):
        name = f"L{len(self.labels)}"
        self.labels[name] = None
        return name

    def place(self, name):
        self.labels[name] = len(self.code)

    def resolve(self):
        for ins in self.code:
            if ins["op"] in JUMPS:
                ins["arg"] = self.labels[ins["arg"]]
            elif ins["op"] == "CALL":
                ins["arg"] = self.funcs[ins["arg"]]["addr"]

    def at(self, node):
        saved, self.node = self.node, node
        return saved

    def lookup(self, node):
        for scope in reversed(self.scopes or []):
            if node.value in scope:
                return scope[node.value], ""
        if node.value in self.globals:
            return self.globals[node.value], "G"
        self.error(node, f"'{node.value}' undeclared")

    def declare(self, node, scope, prefix):
        saved = self.at(node)
        if node.type == "void":
            self.error(node, f"variable '{node.value}' declared void")
        if node.value in scope:
            self.error(node, f"'{node.value}' redeclared")
        slot = len(self.globals) if prefix else self.next_slot
        is_array = node.kind == "Array"
        if is_array:
            size = node.children[0].value
            if size <= 0 or len(node.children) - 1 > size:
                self.error(node, f"bad size of array '{node.value}'")
            self.emit("NEWARR", size)
        elif node.children:
            self.expr(node.children[0])
        else:
            self.emit("PUSH", 0)
        scope[node.value] = (slot, is_array)
        if not prefix:
            self.next_slot += 1
            self.max_slot = max(self.max_slot, self.next_slot)
        self.emit(prefix + "STORE", slot)
        self.emit("POP")
        if is_array:
            for i, e in enumerate(node.children[1:]):
                self.emit(prefix + "LOAD", slot)
                self.emit("PUSH", i)
                self.expr(e)
                self.emit("ASTORE")
                self.emit("POP")
        self.node = saved

    def function(self, func):
        saved = self.at(func)
        self.funcs[func.value]["addr"] = len(self.code)
        params = func.children[0].children
        self.scopes = [{}]
        self.next_slot = 0
        self.max_slot = 0
        for p in params:
            if p.value in self.scopes[0]:
                self.error(p, f"parameter '{p.value}' repeated")
            self.scopes[0][p.value] = (self.next_slot, False)
            self.next_slot += 1
        self.max_slot = self.next_slot
        enter = len(self.code)
        self.emit("ENTER", 0)
        self.stmt(func.children[1])
        self.emit("PUSH", 0)
        self.emit("RET")
        self.code[enter]["arg"] = self.max_slot
        self.scopes = None
        self.node = saved

    def stmt(self, node):
        saved = self.at(node)
        k = node.kind
        if k == "Block":
            self.scopes.append({})
            mark = self.next_slot
            for s in node.children:
                self.stmt(s)
            self.next_slot = mark
            self.scopes.pop()
        elif k == "Decl":
            for d in node.children:
                self.declare(d, self.scopes[-1], "")
        elif k == "ExprStmt":
            self.expr(node.children[0])
            self.emit("POP")
        elif k == "Empty":
            pass
        elif k == "If":
            other, end = self.label(), self.label()
            self.expr(node.children[0])
            self.emit("JZ", other)
            self.stmt(node.children[1])
            if len(node.children) == 3:
                self.emit("JMP", end)
            self.place(other)
            if len(node.children) == 3:
                self.stmt(node.children[2])
            self.place(end)
        elif k == "While":
            top, end = self.label(), self.label()
            self.place(top)
            self.expr(node.children[0])
            self.emit("JZ", end)
            self.loop(node.children[1], end, top)
            self.emit("JMP", top)
            self.place(end)
        elif k == "DoWhile":
            top, test, end = self.label(), self.label(), self.label()
            self.place(top)
            self.loop(node.children[0], end, test)
            self.place(test)
            self.expr(node.children[1])
            self.emit("JNZ", top)
            self.place(end)
        elif k == "For":
            init, cond, step, body = node.children
            top, nxt, end = self.label(), self.label(), self.label()
            self.scopes.append({})
            mark = self.next_slot
            if init.kind == "Decl":
                self.stmt(init)
            elif init.kind != "Empty":
                self.expr(init)
                self.emit("POP")
            self.place(top)
            if cond.kind != "Empty":
                self.expr(cond)
                self.emit("JZ", end)
            self.loop(body, end, nxt)
            self.place(nxt)
            if step.kind != "Empty":
                self.expr(step)
                self.emit("POP")
            self.emit("JMP", top)
            self.place(end)
            self.next_slot = mark
            self.scopes.pop()
        elif k == "Return":
            if node.children:
                self.expr(node.children[0])
            else:
                self.emit("PUSH", 0)
            self.emit("RET")
        elif k in ("Break", "Continue"):
            if not self.loops:
                self.error(node, f"'{k.lower()}' outside a loop")
            self.emit("JMP", self.loops[-1][0 if k == "Break" else 1])
        else:
            self.error(node, f"unknown statement {k}")
        self.node = saved

    def loop(self, body, brk, cont):
        self.loops.append((brk, cont))
        self.stmt(body)
        self.loops.pop()

    def ref(self, node):
        (slot, is_array), prefix = self.lookup(node)
        if node.kind == "Name" and is_array:
            self.error(node, f"'{node.value}' is an array")
        if node.kind == "Index" and not is_array:
            self.error(node, f"'{node.value}' is not an array")
        return slot, prefix

    def expr(self, node):
        saved = self.at(node)
        k = node.kind
        value = fold(node)
        if value is not None:
            self.emit("PUSH", value)
        elif k == "Str":
            if node.value not in self.strings:
                self.strings.append(node.value)
            self.emit("PUSHS", self.strings.index(node.value))
        elif k == "Name":
            slot, prefix = self.ref(node)
            self.emit(prefix + "LOAD", slot)
        elif k == "Index":
            self.element(node)
            self.emit("ALOAD")
        elif k == "Bin":
            self.expr(node.children[0])
            self.expr(node.children[1])
            self.emit(BIN_OPS[node.value])
        elif k == "Logic":
            short, end = self.label(), self.label()
            jump = "JZ" if node.value == "&&" else "JNZ"
            self.expr(node.children[0])
            self.emit(jump, short)
            self.expr(node.children[1])
            self.emit(jump, short)
            self.emit("PUSH", 1 if node.value == "&&" else 0)
            self.emit("JMP", end)
            self.place(short)
            self.emit("PUSH", 0 if node.value == "&&" else 1)
            self.place(end)
        elif k == "Unary":
            self.expr(node.children[0])
            self.emit("NEG" if node.value == "-" else "NOT")
        elif k == "Cond":
            other, end = self.label(), self.label()
            self.expr(node.children[0])
            self.emit("JZ", other)
            self.expr(node.children[1])
            self.emit("JMP", end)
            self.place(other)
            self.expr(node.children[2])
            self.place(end)
        elif k == "Assign":
            self.assign(node)
        elif k in ("PreInc", "PostInc"):
            self.incdec(node)
        elif k == "Call":
            self.call(node)
        else:
            self.error(node, f"unknown expression {k}")
        self.node = saved

    def element(self, node):
        slot, prefix = self.ref(node)
        self.emit(prefix + "LOAD", slot)
        self.expr(node.children[0])

    def assign(self, node):
        target, rhs = node.children
        op = None if node.value == "=" else BIN_OPS[node.value[0]]
        if target.kind == "Name":
            slot, prefix = self.ref(target)
            if op:
                self.emit(prefix + "LOAD", slot)
            self.expr(rhs)
            if op:
                self.emit(op)
            self.emit(prefix + "STORE", slot)
        else:
            self.element(target)
            if op:
                self.emit("DUP2")
                self.emit("ALOAD")
            self.expr(rhs)
            if op:
                self.emit(op)
            self.emit("ASTORE")

    def incdec(self, node):
        target = node.children[0]
        op, undo = ("ADD", "SUB") if node.value == "++" else ("SUB", "ADD")
        if target.kind == "Name":
            slot, prefix = self.ref(target)
            self.emit(prefix + "LOAD", slot)
            self.emit("PUSH", 1)
            self.emit(op)
            self.emit(prefix + "STORE", slot)
        else:
            self.element(target)
            self.emit("DUP2")
            self.emit("ALOAD")
            self.emit("PUSH", 1)
            self.emit(op)
            self.emit("ASTORE")
        if node.kind == "PostInc":
            self.emit("PUSH", 1)
            self.emit(undo)

    def call(self, node):
        name, args = node.value, node.children
        if name in ("printf", "putchar"):
            if name == "printf" and (not args or args[0].kind != "Str"):
                self.error(node, "printf needs a format string")
            if name == "putchar" and len(args) != 1:
                self.error(node, "putchar expects 1 argument")
            for a in args:
                self.expr(a)
            self.emit("PRINT", len(args)) if name == "printf" else self.emit("PUTC")
            return
        if name not in self.funcs:
            self.error(node, f"function '{name}' undeclared")
        want = self.funcs[name]["params"]
        if len(args) != want:
            self.error(node, f"'{name}' expects {want} arguments, got {len(args)}")
        for a in args:
            if a.kind == "Str":
                self.error(a, "string literal allowed only in printf")
            self.expr(a)
        self.emit("CALL", name, len(args))

    def program(self):
        return {
            "code": self.code,
            "strings": self.strings,
            "globals": len(self.globals),
            "funcs": {n: f["addr"] for n, f in self.funcs.items()},
        }


def compile_program(tree):
    return Codegen(tree).program()


def listing(prog):
    starts = {addr: name for name, addr in prog["funcs"].items()}
    targets = {ins["arg"] for ins in prog["code"] if ins["op"] in JUMPS}
    lines = []
    if prog["strings"]:
        lines.append(".strings")
        for i, s in enumerate(prog["strings"]):
            lines.append(f"  {i}: {s!r}")
    lines.append(f".globals {prog['globals']}")
    lines.append(".code")
    for addr, ins in enumerate(prog["code"]):
        if addr in starts:
            lines.append(f"{starts[addr]}:")
        elif addr in targets:
            lines.append(f"@{addr}:")
        args = " ".join(str(a) for a in (ins["arg"], ins["arg2"]) if a is not None)
        if ins["op"] == "CALL":
            args += f"  <{next(n for n, a in prog['funcs'].items() if a == ins['arg'])}>"
        lines.append(f"  {addr:04d}  {ins['op']:<7}{args:<16}line {ins['line']}")
    return "\n".join(lines)
