class VMError extends Error {}

function cformat(fmt, args) {
  const rest = args.slice();
  return fmt.replace(/%(-?\d*)([dcs%])/g, (m, width, conv) => {
    if (conv === "%") return "%";
    if (!rest.length) throw new VMError("printf: not enough arguments");
    const v = rest.shift();
    const s = conv === "s" ? String(v) : conv === "c" ? String.fromCharCode(v & 0xff) : String(v);
    if (!width) return s;
    const w = parseInt(width, 10);
    return w < 0 ? s.padEnd(-w) : s.padStart(w);
  });
}

const MAX_FRAMES = 100000;

class VM {
  constructor(prog, write) {
    this.prog = prog;
    this.write = write || (() => {});
    this.reset();
  }

  reset() {
    this.pc = 0;
    this.stack = [];
    this.frames = [{ func: "<start>", ret: -1, locals: [] }];
    this.globals = new Array(this.prog.globals).fill(0);
    this.halted = false;
    this.steps = 0;
    this.output = "";
  }

  print(text) {
    this.output += text;
    this.write(text);
  }

  pop() {
    return this.stack.pop();
  }

  push(v) {
    this.stack.push(v);
  }

  fail(ins, msg) {
    throw new VMError(`line ${ins.line}: error: ${msg}`);
  }

  funcName(addr) {
    for (const [name, a] of Object.entries(this.prog.funcs)) if (a === addr) return name;
    return "?";
  }

  current() {
    return this.prog.code[this.pc];
  }

  step() {
    if (this.halted) return false;
    const ins = this.prog.code[this.pc++];
    const frame = this.frames[this.frames.length - 1];
    const a = ins.arg;
    this.steps++;
    let x, y, v, arr;
    switch (ins.op) {
      case "PUSH": this.push(a); break;
      case "PUSHS": this.push(this.prog.strings[a]); break;
      case "POP": this.pop(); break;
      case "DUP": this.push(this.stack[this.stack.length - 1]); break;
      case "DUP2":
        x = this.stack[this.stack.length - 2];
        y = this.stack[this.stack.length - 1];
        this.push(x);
        this.push(y);
        break;
      case "LOAD": this.push(frame.locals[a]); break;
      case "STORE": frame.locals[a] = this.stack[this.stack.length - 1]; break;
      case "GLOAD": this.push(this.globals[a]); break;
      case "GSTORE": this.globals[a] = this.stack[this.stack.length - 1]; break;
      case "NEWARR": this.push(new Array(a).fill(0)); break;
      case "ALOAD":
        x = this.pop();
        arr = this.pop();
        if (x < 0 || x >= arr.length) this.fail(ins, `index ${x} out of bounds of array[${arr.length}]`);
        this.push(arr[x]);
        break;
      case "ASTORE":
        v = this.pop();
        x = this.pop();
        arr = this.pop();
        if (x < 0 || x >= arr.length) this.fail(ins, `index ${x} out of bounds of array[${arr.length}]`);
        arr[x] = v;
        this.push(v);
        break;
      case "ADD": y = this.pop(); x = this.pop(); this.push((x + y) | 0); break;
      case "SUB": y = this.pop(); x = this.pop(); this.push((x - y) | 0); break;
      case "MUL": y = this.pop(); x = this.pop(); this.push(Math.imul(x, y)); break;
      case "DIV":
      case "MOD":
        y = this.pop();
        x = this.pop();
        if (y === 0) this.fail(ins, "division by zero");
        this.push(ins.op === "DIV" ? Math.trunc(x / y) | 0 : (x % y) | 0);
        break;
      case "NEG": this.push(-this.pop() | 0); break;
      case "NOT": this.push(this.pop() ? 0 : 1); break;
      case "EQ": y = this.pop(); x = this.pop(); this.push(x === y ? 1 : 0); break;
      case "NE": y = this.pop(); x = this.pop(); this.push(x !== y ? 1 : 0); break;
      case "LT": y = this.pop(); x = this.pop(); this.push(x < y ? 1 : 0); break;
      case "LE": y = this.pop(); x = this.pop(); this.push(x <= y ? 1 : 0); break;
      case "GT": y = this.pop(); x = this.pop(); this.push(x > y ? 1 : 0); break;
      case "GE": y = this.pop(); x = this.pop(); this.push(x >= y ? 1 : 0); break;
      case "JMP": this.pc = a; break;
      case "JZ": if (!this.pop()) this.pc = a; break;
      case "JNZ": if (this.pop()) this.pc = a; break;
      case "CALL": {
        if (this.frames.length >= MAX_FRAMES) this.fail(ins, "stack overflow");
        const args = this.stack.splice(this.stack.length - ins.arg2, ins.arg2);
        this.frames.push({ func: this.funcName(a), ret: this.pc, locals: args });
        this.pc = a;
        break;
      }
      case "ENTER":
        while (frame.locals.length < a) frame.locals.push(0);
        break;
      case "RET":
        v = this.pop();
        this.pc = this.frames.pop().ret;
        this.push(v);
        break;
      case "PRINT": {
        const args = this.stack.splice(this.stack.length - a, a);
        let text;
        try {
          text = cformat(args[0], args.slice(1));
        } catch (e) {
          this.fail(ins, e.message);
        }
        this.print(text);
        this.push(text.length);
        break;
      }
      case "PUTC":
        v = this.pop();
        this.print(String.fromCharCode(v & 0xff));
        this.push(v);
        break;
      case "HALT": this.halted = true; this.pc--; break;
      default: this.fail(ins, `bad instruction ${ins.op}`);
    }
    return !this.halted;
  }

  run(limit = Infinity) {
    let n = 0;
    while (!this.halted && n < limit) {
      this.step();
      n++;
    }
    return this.halted;
  }
}

if (typeof module !== "undefined") {
  module.exports = { VM, VMError };
  if (require.main === module) {
    const src = require("fs").readFileSync(process.argv[2] || 0, "utf8");
    const vm = new VM(JSON.parse(src), (t) => process.stdout.write(t));
    try {
      vm.run();
    } catch (e) {
      process.stderr.write((e instanceof VMError ? e.message : e.stack) + "\n");
      process.exitCode = 1;
    }
  }
}
