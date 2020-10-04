import sys
from types import ModuleType
from code import InteractiveConsole
from . import compile, exec


class InteractiveShell(InteractiveConsole):

    def __init__(self):
        super().__init__({}, "<console>")
        del self.__dict__['compile']

    def compile(self, source, filename, symbol):
        try:
            return compile(source, filename, tuple(self.locals))
        except EOFError:
            pass

    def runcode(self, code):
        try:
            exec(code, self.locals)
        except SystemExit:
            raise
        except:
            self.showtraceback()


if len(sys.argv) > 1:
    del sys.argv[0]
    mod = ModuleType("__main__")
    sys.modules['__main__'] = mod.__dict__
    filename = sys.argv[0]

    with open(filename, "r") as f:
        code = compile(f.read(), filename)

    exec(code, mod.__dict__)
else:
    shell = InteractiveShell()
    shell.interact("Mulan2020")
