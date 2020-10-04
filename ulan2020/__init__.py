from .compile import compile

class MatchException(Exception):
    def __init__(self, value):
        self.value = value

class New:
    def __init__(self, cell):
        self.cell = cell

    def __umatch__(self, other):
        self.cell.cell_contents = other
        return True

class GlobalNew:
    def __init__(self, globals, name):
        self.globals = globals
        self.name = name

    def __umatch__(self, other):
        self.globals[self.name] = other
        return True


class GlobalVar:
    def __init__(self, globals, name):
        self.globals = globals
        self.name = name

    def __umatch__(self, other):
        return self.globals[self.name] == other

class Var:
    def __init__(self, cell):
        self.cell = cell

    def __umatch__(self, other):
        return self.cell.cell_contents == other

class Value:
    def __init__(self, value):
        self.value = value

    def __umatch__(self, other):
        return self.value == other

_exec = exec

builtins = {
    ".gnew": GlobalNew,
    ".gvar": GlobalVar,
    ".globals": globals,
    ".new": New,
    ".var": Var,
    ".value": Value,
    ".MatchException": MatchException,
    "__import__": __import__
}

def exec(code, globals=None, locals=None):
    if globals is None:
        globals = dict()
    if "__builtins__" not in globals:
        globals["__builtins__"] = builtins
    if locals is None:
        locals = {}
    _exec(code, globals, locals)
