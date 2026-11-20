# Лабораторна робота: синтаксичний аналізатор на Lex/YACC

Автор: Кара Альбіна, ТК-32

Транслятор підмножини мови C, написаний на Python з PLY (реалізація Lex/YACC, LALR(1)).

- `minic/lexer.py` — лексер (`ply.lex`);
- `minic/parser.py` — граматика та побудова AST (`ply.yacc`);
- `minic/interp.py` — обчислення програми обходом AST;
- `minic/codegen.py` — трансляція AST у байт-код стекової віртуальної машини зі згорткою констант;
- `vm/vm.js` — віртуальна машина на JavaScript;
- `viz/template.html` — інтерактивна візуалізація AST на d3.js з покроковим виконанням байт-коду;
- `theory/` — граматики, на яких видно конфлікти shift/reduce і reduce/reduce та різницю між SLR і LALR.

Підмножина C: `int`, `void`, глобальні й локальні змінні, масиви з ініціалізацією, функції з рекурсією, `if/else`, `while`, `do-while`, `for`, `break`, `continue`, `return`, `?:`, `&&`, `||`, `!`, порівняння, арифметика, `= += -= *= /= %=`, `++`, `--`, `printf`, `putchar`.

## Запуск

Потрібні Python 3 і Node.js.

```
pip install -r requirements.txt
python -m minic tree examples/fact.c
python -m minic run examples/fact.c
python -m minic bc examples/fact.c
python -m minic vm examples/fact.c
python -m minic html examples/bubble.c
python tests/run.py
```

`tree` друкує AST, `json` виводить AST у JSON, `run` виконує програму інтерпретатором, `bc` друкує байт-код, `vm` виконує байт-код у віртуальній машині, `html` створює сторінку `out/<назва>.html`, `grammar <тека>` записує звіт PLY `parser.out`.

`tests/run.py` порівнює вивід інтерпретатора й віртуальної машини з еталонами `examples/*.out`, отриманими від gcc, і перевіряє повідомлення про помилки на `tests/errors/*.c`.
