import ply.lex as lex

from minic import MiniCError

reserved = {
    "int": "INT",
    "void": "VOID",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "do": "DO",
    "for": "FOR",
    "return": "RETURN",
    "break": "BREAK",
    "continue": "CONTINUE",
}

tokens = [
    "ID", "NUM", "CHAR", "STRING",
    "EQ", "NE", "LE", "GE", "AND", "OR", "INC", "DEC",
    "ADD_ASSIGN", "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN",
] + list(reserved.values())

literals = "+-*/%<>=!?:;,(){}[]"

t_ignore = " \t\r"

t_EQ = r"=="
t_NE = r"!="
t_LE = r"<="
t_GE = r">="
t_AND = r"&&"
t_OR = r"\|\|"
t_INC = r"\+\+"
t_DEC = r"--"
t_ADD_ASSIGN = r"\+="
t_SUB_ASSIGN = r"-="
t_MUL_ASSIGN = r"\*="
t_DIV_ASSIGN = r"/="
t_MOD_ASSIGN = r"%="

ESCAPES = {"n": "\n", "t": "\t", "0": "\0", "\\": "\\", "'": "'", '"': '"'}


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def t_COMMENT(t):
    r"/\*(.|\n)*?\*/"
    t.lexer.lineno += t.value.count("\n")


def t_LINE_COMMENT(t):
    r"//[^\n]*"


def t_PREPROC(t):
    r"\#[^\n]*"


def t_ID(t):
    r"[A-Za-z_][A-Za-z_0-9]*"
    t.type = reserved.get(t.value, "ID")
    return t


def t_NUM(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_CHAR(t):
    r"'(\\.|[^\\'\n])'"
    t.value = ord(unescape(t.value[1:-1]))
    return t


def t_STRING(t):
    r'"(\\.|[^\\"\n])*"'
    t.value = unescape(t.value[1:-1])
    return t


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


def t_error(t):
    raise MiniCError(f"line {t.lexer.lineno}: unexpected character {t.value[0]!r}")


def make_lexer():
    return lex.lex()
