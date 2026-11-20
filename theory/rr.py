from pathlib import Path

import ply.lex as lex
import ply.yacc as yacc

tokens = ("ID",)
literals = ";"
t_ignore = " "
t_ID = r"[a-z]+"


def t_error(t):
    raise SyntaxError(t.value[0])


def p_stmt(p):
    """stmt : decl ';'
            | expr ';'"""
    p[0] = p[1]


def p_decl(p):
    "decl : ID"
    p[0] = f"оголошення {p[1]}"


def p_expr(p):
    "expr : ID"
    p[0] = f"вираз {p[1]}"


def p_error(t):
    raise SyntaxError(t)


out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
parser = yacc.yacc(debug=True, debugfile="rr.txt", outputdir=str(out), write_tables=False)
print("звіт про стани: theory/out/rr.txt")
print("x ;  ->", parser.parse("x ;", lexer=lex.lex()))
