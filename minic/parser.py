import os

import ply.yacc as yacc

from minic import MiniCError
from minic.ast import Node, number
from minic.lexer import make_lexer, tokens

precedence = (
    ("nonassoc", "IFX"),
    ("nonassoc", "ELSE"),
    ("right", "=", "ADD_ASSIGN", "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN"),
    ("right", "?", ":"),
    ("left", "OR"),
    ("left", "AND"),
    ("left", "EQ", "NE"),
    ("left", "<", ">", "LE", "GE"),
    ("left", "+", "-"),
    ("left", "*", "/", "%"),
    ("right", "UMINUS", "!"),
)


def p_program(p):
    "program : items"
    p[0] = Node("Program", children=p[1], line=1)


def p_items(p):
    """items : items item
             | item"""
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1]


def p_item_func(p):
    "item : func"
    p[0] = [p[1]]


def p_item_decl(p):
    "item : decl"
    p[0] = [p[1]]


def p_type(p):
    """type : INT
            | VOID"""
    p[0] = p[1]


def p_func(p):
    "func : type ID '(' params ')' block"
    p[0] = Node("Func", p[2], [Node("Params", children=p[4], line=p.lineno(2)), p[6]], p.lineno(2), p[1])


def p_params_empty(p):
    """params : VOID
              | empty"""
    p[0] = []


def p_params(p):
    "params : plist"
    p[0] = p[1]


def p_plist(p):
    """plist : plist ',' param
             | param"""
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


def p_param(p):
    "param : type ID"
    p[0] = Node("Param", p[2], line=p.lineno(2), type=p[1])


def p_decl(p):
    "decl : type dlist ';'"
    for d in p[2]:
        d.type = p[1]
    p[0] = Node("Decl", children=p[2], line=p.lineno(3))


def p_dlist(p):
    """dlist : dlist ',' declarator
             | declarator"""
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


def p_declarator_var(p):
    """declarator : ID
                  | ID '=' expr"""
    p[0] = Node("Var", p[1], [p[3]] if len(p) == 4 else [], p.lineno(1))


def p_declarator_array(p):
    """declarator : ID '[' NUM ']'
                  | ID '[' NUM ']' '=' '{' elist '}'
                  | ID '[' ']' '=' '{' elist '}'"""
    if len(p) == 5:
        size, init = p[3], []
    elif len(p) == 9:
        size, init = p[3], p[7]
    else:
        size, init = len(p[6]), p[6]
    p[0] = Node("Array", p[1], [Node("Num", size, line=p.lineno(1))] + init, p.lineno(1))


def p_elist(p):
    """elist : elist ',' expr
             | expr"""
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


def p_block(p):
    "block : '{' stmts '}'"
    p[0] = Node("Block", children=p[2], line=p.lineno(1))


def p_stmts(p):
    """stmts : stmts stmt
             | empty"""
    p[0] = p[1] + [p[2]] if len(p) == 3 else []


def p_stmt_simple(p):
    """stmt : block
            | decl"""
    p[0] = p[1]


def p_stmt_expr(p):
    "stmt : expr ';'"
    p[0] = Node("ExprStmt", children=[p[1]], line=p[1].line)


def p_stmt_empty(p):
    "stmt : ';'"
    p[0] = Node("Empty", line=p.lineno(1))


def p_stmt_if(p):
    "stmt : IF '(' expr ')' stmt %prec IFX"
    p[0] = Node("If", children=[p[3], p[5]], line=p.lineno(1))


def p_stmt_if_else(p):
    "stmt : IF '(' expr ')' stmt ELSE stmt"
    p[0] = Node("If", children=[p[3], p[5], p[7]], line=p.lineno(1))


def p_stmt_while(p):
    "stmt : WHILE '(' expr ')' stmt"
    p[0] = Node("While", children=[p[3], p[5]], line=p.lineno(1))


def p_stmt_do(p):
    "stmt : DO stmt WHILE '(' expr ')' ';'"
    p[0] = Node("DoWhile", children=[p[2], p[5]], line=p.lineno(1))


def p_stmt_for(p):
    "stmt : FOR '(' forinit optexpr ';' optexpr ')' stmt"
    p[0] = Node("For", children=[p[3], p[4], p[6], p[8]], line=p.lineno(1))


def p_forinit(p):
    """forinit : decl
               | optexpr ';'"""
    p[0] = p[1]


def p_optexpr(p):
    """optexpr : expr
               | empty"""
    p[0] = p[1] if p[1] is not None else Node("Empty", line=p.lineno(0))


def p_stmt_return(p):
    "stmt : RETURN optexpr ';'"
    p[0] = Node("Return", children=[] if p[2].kind == "Empty" else [p[2]], line=p.lineno(1))


def p_stmt_jump(p):
    """stmt : BREAK ';'
            | CONTINUE ';'"""
    p[0] = Node(p[1].capitalize(), line=p.lineno(1))


def p_expr_assign(p):
    """expr : lvalue '=' expr
            | lvalue ADD_ASSIGN expr
            | lvalue SUB_ASSIGN expr
            | lvalue MUL_ASSIGN expr
            | lvalue DIV_ASSIGN expr
            | lvalue MOD_ASSIGN expr"""
    p[0] = Node("Assign", p[2], [p[1], p[3]], p[1].line)


def p_expr_ternary(p):
    "expr : expr '?' expr ':' expr"
    p[0] = Node("Cond", children=[p[1], p[3], p[5]], line=p[1].line)


def p_expr_logic(p):
    """expr : expr OR expr
            | expr AND expr"""
    p[0] = Node("Logic", p[2], [p[1], p[3]], p[1].line)


def p_expr_binary(p):
    """expr : expr EQ expr
            | expr NE expr
            | expr '<' expr
            | expr '>' expr
            | expr LE expr
            | expr GE expr
            | expr '+' expr
            | expr '-' expr
            | expr '*' expr
            | expr '/' expr
            | expr '%' expr"""
    p[0] = Node("Bin", p[2], [p[1], p[3]], p[1].line)


def p_expr_unary(p):
    """expr : '-' expr %prec UMINUS
            | '!' expr"""
    p[0] = Node("Unary", p[1], [p[2]], p.lineno(1))


def p_expr_pre(p):
    """expr : INC lvalue
            | DEC lvalue"""
    p[0] = Node("PreInc", p[1], [p[2]], p.lineno(1))


def p_expr_post(p):
    """expr : lvalue INC
            | lvalue DEC"""
    p[0] = Node("PostInc", p[2], [p[1]], p[1].line)


def p_expr_group(p):
    "expr : '(' expr ')'"
    p[0] = p[2]


def p_expr_num(p):
    """expr : NUM
            | CHAR"""
    p[0] = Node("Num", p[1], line=p.lineno(1))


def p_expr_str(p):
    "expr : STRING"
    p[0] = Node("Str", p[1], line=p.lineno(1))


def p_expr_call(p):
    "expr : ID '(' args ')'"
    p[0] = Node("Call", p[1], p[3], p.lineno(1))


def p_args(p):
    """args : elist
            | empty"""
    p[0] = p[1] or []


def p_expr_lvalue(p):
    "expr : lvalue"
    p[0] = p[1]


def p_lvalue_id(p):
    "lvalue : ID"
    p[0] = Node("Name", p[1], line=p.lineno(1))


def p_lvalue_index(p):
    "lvalue : ID '[' expr ']'"
    p[0] = Node("Index", p[1], [p[3]], p.lineno(1))


def p_empty(p):
    "empty :"
    p[0] = None


def p_error(t):
    if t is None:
        raise MiniCError("syntax error: unexpected end of input")
    raise MiniCError(f"line {t.lineno}: syntax error near {t.value!r}")


def make_parser(debug=False, outdir=None):
    kw = {"write_tables": False, "debug": debug, "errorlog": yacc.NullLogger()}
    if debug:
        kw["errorlog"] = yacc.PlyLogger(open(os.devnull, "w"))
        kw["outputdir"] = outdir or os.getcwd()
    return yacc.yacc(**kw)


def parse(text):
    lexer = make_lexer()
    tree = make_parser().parse(text, lexer=lexer)
    return number(tree)
