import unittest
from unittest.case import _BaseTestCaseContext
from contextlib import redirect_stdout, contextmanager
from io import StringIO
from ..compile import compile


def run(source):
    code = compile(source, "<stdin>")
    exec(code, dict())

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
