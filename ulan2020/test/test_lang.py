import unittest
from unittest.case import _BaseTestCaseContext
from contextlib import redirect_stdout, contextmanager
from io import StringIO
from .. import compile, exec, MatchException


def run(source):
    code = compile(source, "<stdin>")
    d = dict()
    exec(code, d)
    return d

@contextmanager
def assert_prints_context(test_case, output):
    buf = StringIO()
    with redirect_stdout(buf):
        yield
    if buf.getvalue() == output:
        return
    raise test_case.failureException(
        test_case._formatMessage(
            None,
            "{!r} does not match {!r}".format(buf.getvalue(), output)))


class TestCase(unittest.TestCase):

    def assertPrints(self, output):
        return assert_prints_context(self, output)


class FileTest(TestCase):

    def test_print(self):
        with self.assertPrints("ok"):
            run("::print({[ok]}, end:{[]});")

    def test_if(self):
        with self.assertPrints("1\n"):
            run("if 1: ::print(1); else: ::print(2); end")

        with self.assertPrints("2\n"):
            run("if 0: ::print(1); else: ::print(2); end")

    def test_match(self):
        self.assertEqual(run("let x = 1;")["x"], 1)
        self.assertEqual(run("let x = 1; let x = 1;")["x"], 1)
        with self.assertRaises(MatchException):
            self.assertEqual(run("let x = 1; let x = 2;")["x"], 1)

    def test_var_not_defined(self):
        with self.assertRaises(KeyError):
            run("x;")

    def test_if_match(self):
        with self.assertPrints("1\n"):
            run("if let 1 = 1: ::print(1); end")

        with self.assertPrints("2\n"):
            run("if let 2 = 1: ::print(1); else: ::print(2); end")

    def test_unsafe(self):
        with self.assertRaises(NameError):
            run("if let 1 = 2: let x = 2; end ::print(x);")

    def test_arguments(self):
        self.assertEqual(run("def f(): return 1; end")['f'](), 1)
        self.assertEqual(run("def f(a): return a; end")['f'](a=1), 1)
        self.assertEqual(run("def f(a): return a; end")['f'](1), 1)

        with self.assertRaises(MatchException):
            run("def f(a:2): return 1; end")['f'](1)

        self.assertEqual(run("def f(b=1): return b; end")['f'](), 1)
        self.assertEqual(run("def f(b=1): return b; end")['f'](2), 2)

        with self.assertRaises(MatchException):
            run("def f(a, b: a=2): end")['f'](1)

        self.assertEqual(run("def f(*a): return a; end")['f'](1,2,3), (1,2,3))

        with self.assertRaises(MatchException):
            run("def f(a:2, *args): end")['f'](1, 2, 3)

        self.assertEqual(run("def f(*, b): return b; end")['f'](b=1), 1)
        with self.assertRaises(TypeError):
            run("def f(*, b): return b; end")['f'](1)
        with self.assertRaises(MatchException):
            run("def f(*, b:1): return 1; end")['f'](b=2)
        self.assertEqual(run("def f(*, b=1): return b; end")['f'](), 1)

        self.assertEqual(run("def f(**kw): return kw; end")['f'](a=1), {"a":1})
