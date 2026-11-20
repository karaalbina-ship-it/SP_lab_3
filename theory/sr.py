import sys
from pathlib import Path

import ply.lex as lex
import ply.yacc as yacc

FIXED = "--fixed" in sys.argv

tokens = ("NUM",)
literals = "+*"
t_ignore = " "


def t_NUM(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_error(t):
    raise SyntaxError(t.value[0])


if FIXED:
    precedence = (
        ("left", "+"),
        ("left", "*"),
    )


def p_e_add(p):
    "e : e '+' e"
    p[0] = f"({p[1]} + {p[3]})"


def p_e_mul(p):
    "e : e '*' e"
    p[0] = f"({p[1]} * {p[3]})"


def p_e_num(p):
    "e : NUM"
    p[0] = str(p[1])


def p_error(t):
    raise SyntaxError(t)


out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
name = "sr_fixed" if FIXED else "sr"
parser = yacc.yacc(debug=True, debugfile=f"{name}.txt", outputdir=str(out), write_tables=False)
print(f"звіт про стани: theory/out/{name}.txt")
for text in ("2 + 3 * 4", "2 * 3 + 4", "1 + 2 + 3"):
    tree = parser.parse(text, lexer=lex.lex())
    print(f"{text:<10} -> {tree} = {eval(tree)}")
