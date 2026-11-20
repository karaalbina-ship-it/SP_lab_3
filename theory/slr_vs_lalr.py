from pathlib import Path

import ply.lex as lex
import ply.yacc as yacc

tokens = ("ID",)
literals = "=*"
t_ignore = " "
t_ID = r"[a-z]+"


def t_error(t):
    raise SyntaxError(t.value[0])


def p_s_assign(p):
    "s : l '=' r"
    p[0] = f"присвоєння {p[1]} := {p[3]}"


def p_s_value(p):
    "s : r"
    p[0] = f"значення {p[1]}"


def p_l_deref(p):
    "l : '*' r"
    p[0] = f"*{p[2]}"


def p_l_id(p):
    "l : ID"
    p[0] = p[1]


def p_r(p):
    "r : l"
    p[0] = p[1]


def p_error(t):
    raise SyntaxError(t)


out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
for method in ("SLR", "LALR"):
    print(f"--- {method}")
    parser = yacc.yacc(method=method, debug=True, debugfile=f"{method.lower()}.txt",
                       outputdir=str(out), write_tables=False)
    print(f"звіт про стани: theory/out/{method.lower()}.txt")
    for text in ("*p = q", "*p"):
        try:
            print(f"{text:<7} ->", parser.parse(text, lexer=lex.lex()))
        except SyntaxError as e:
            print(f"{text:<7} -> синтаксична помилка на {e}")
