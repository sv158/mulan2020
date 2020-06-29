import unittest
from ..compile.parse import Lexer, Parser, Node, File
from typing import _GenericAlias, Union

def check_type(node, ty):
    if isinstance(ty, _GenericAlias):
        if ty.__origin__ is Union:
            for t in ty.__args__:
                if check_type(node, t):
                    return True
            # print("failed 1", node, ty)
            return False
        elif ty.__origin__ is list:
            if not isinstance(node, list):
                return False
            t = ty.__args__[0]
            for elem in node:
                if not check_type(elem, t):
                    # print("failed 2", elem, ty)
                    return False
            return True
        else:
            raise NotImplementedError

    if not isinstance(node, ty):
        return False

    if not isinstance(node, Node):
        return True

    ty = type(node)

    for key, value in getattr(ty, "__annotations__", {}).items():
        if not check_type(getattr(node, key, None), value):
            # print("failed 3", node, ty)
            return False

    return True

class TestCase(unittest.TestCase):

    def parse(self, text, filename=__file__):
        lexer = Lexer(filename)
        parser = Parser(filename, text)

        with self.subTest(text):
            self.assertTrue(check_type(parser.parse(lexer.tokenize(text)), File))


class FileTest(TestCase):

    def test_shebang(self):
        self.parse("#!/usr/bin/env python3")


class StatementTest(TestCase):

    def test_return(self):
        self.parse("return 1;")

    def test_if(self):
        self.parse("if 1: return 1; end")
        self.parse("if 1: return 1; else: return 2; end")
        self.parse("if 1: return 1; else if 2: return 2; end")


class ExpressionTest(TestCase):

    def test_literal(self):
        self.parse("1;")

    def test_variable(self):
        self.parse("a;")

    def test_module(self):
        self.parse("::;")
        self.parse("::mod::;")
        self.parse("mod::;")
        self.parse("mod::mod::;")

    def test_modattr(self):
        self.parse("mod::a;")
        self.parse("::a;")

    def test_subscript(self):
        self.parse("a[1];")
        self.parse("a[1,2];")
        self.parse("a[1,];")
        self.parse("a[1][2];")

    def test_attribute(self):
        self.parse("a->b;")
        self.parse("a->b->c;")

    def test_paren(self):
        self.parse("(a);")

    def test_tuple(self):
        self.parse("();")
        self.parse("(a,);")
        self.parse("(a, b);")
        self.parse("(*a);")
        self.parse("(a, *b);")
        self.parse("(a, *b, *c);")

    def test_list(self):
        self.parse("[];")
        self.parse("[a];")
        self.parse("[a, b];")
        self.parse("[*a];")
        self.parse("[a, *b];")
        self.parse("[a, *b, *c];")

    def test_set(self):
        self.parse("{/};")
        self.parse("{a};")
        self.parse("{a, b};")
        self.parse("{*a};")
        self.parse("{a, *b};")
        self.parse("{a, *b, *c};")

    def test_dict(self):
        self.parse("{};")
        self.parse("{a:1};")
        self.parse("{a:1, **b};")
        self.parse("{a:1, **b, c:1};")

    def test_binop(self):
        self.parse("1 .gt. 2;")

    def test_unop(self):
        self.parse(".not. 2;")

    def test_call(self):
        self.parse("f();")
        self.parse("f(a);")
        self.parse("f(a, b);")
        self.parse("f(a, b, *c);")
        self.parse("f(a, b, *c, d:1);")
        self.parse("f(a, b, c:1, *d);")
        self.parse("f(a, b, *c, d:1, *e);")
        self.parse("f(a, b, *c, **kw, *e);")
        self.parse("f{};")
        self.parse("f{a, b:c};")
        self.parse("f{a, b:c, **kw};")
        self.parse("f{a, b:c, **kw, c:d};")

    def test_function(self):
        self.parse("def f(): end")
        self.parse("def f(a): end")
        self.parse("def f(a, b): end")

        self.parse("def f(b=1): end")
        self.parse("def f(b=1, c=1): end")
        self.parse("def f(a, b=1): end")
        self.parse("def f(a, b, c=1): end")
        self.parse("def f(a, b=1, c=1): end")

        self.parse("def f(*a): end")
        self.parse("def f(*a, b): end")
        self.parse("def f(a, *b): end")
        self.parse("def f(a, *b, c): end")
        self.parse("def f(b=1, *c): end")
        self.parse("def f(a, *c, b=1): end")
        self.parse("def f(a, b=1, *c): end")
        self.parse("def f(a, b=1, *c, d=1): end")
        self.parse("def f(a, b=1, *c, d=1, e): end")

        self.parse("def f(**kw): end")
        self.parse("def f(a, **kw): end")
        self.parse("def f(b=1, **kw): end")
        self.parse("def f(a, b=1, **kw): end")
        self.parse("def f(*a, **kw): end")
        self.parse("def f(*a, b, **kw): end")
        self.parse("def f(a, *b, **kw): end")
        self.parse("def f(a, *b, c, **kw): end")
        self.parse("def f(b=1, *c, **kw): end")
        self.parse("def f(a, *c, b=1, **kw): end")
        self.parse("def f(a, b=1, *c, **kw): end")
        self.parse("def f(a, b=1, *c, d:f=1, **kw): end")
        self.parse("def f(a, b=1, *c, d=1, e, **kw): end")


class PatternTest(TestCase):

    def test_literal(self):
        self.parse("let 1 = 1;")

    def test_variable(self):
        self.parse("let x = 1;")

    def test_and(self):
        self.parse("let x is y is z = 1;")
        self.parse("let (a is b,) = 1;")

    def test_tuple(self):
        self.parse("let () = 1;")

    def test_tuple(self):
        self.parse("let () = 1;")
        self.parse("let (a,) = 1;")
        self.parse("let (a, b) = 1;")
        self.parse("let (*a) = 1;")
        self.parse("let (a, *a) = 1;")

        self.parse("let (a, *a, a, *a, a) = 1;")

    def test_list(self):
        self.parse("let [] = 1;")
        self.parse("let [a] = 1;")
        self.parse("let [a, b] = 1;")
        self.parse("let [*a] = 1;")
        self.parse("let [a, *a] = 1;")
        self.parse("let [a, *a, a, *a, a] = 1;")

    def test_set(self):
        self.parse("let {/} = 1;")
        self.parse("let {a} = 1;")
        self.parse("let {a, b} = 1;")
        self.parse("let {*a} = 1;")
        self.parse("let {a, *a} = 1;")
        self.parse("let {a, *a, a, *a, a} = 1;")

    def test_dict(self):
        self.parse("let {} = 1;")
        self.parse("let {1: a} = 1;")
        self.parse("let {1: a, **b} = 1;")
        self.parse("let {1: a, **b, 2:c} = 1;")

    def test_cons(self):
        self.parse("let std::int(x) = 1;")
        self.parse("let f() = 1;")
        self.parse("let f(x) = 1;")
        self.parse("let f(x, y) = 1;")
        self.parse("let f(x, y, *a) = 1;")
        self.parse("let f(x, y, *a, z) = 1;")
        self.parse("let f(x, y, a:1) = 1;")
        self.parse("let f(x, y, a=1) = 1;")
        self.parse("let f(x, y, *a, b=1) = 1;")
        self.parse("let f(x, y, a:1, *b) = 1;")
        self.parse("let f(x, y, *a, b:1, *c) = 1;")
        self.parse("let f(x, y, *a, b=1, *c) = 1;")
        self.parse("let f(x, y, *a, **kw, *c) = 1;")
        self.parse("let f{} = 1;")
        self.parse("let f{a} = 1;")
        self.parse("let f{a=2} = 1;")
        self.parse("let f{a:b} = 1;")
        self.parse("let f{a:b=1} = 1;")
        self.parse("let f{a:b, c, **kw} = 1;")
