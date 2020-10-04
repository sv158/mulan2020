from contextlib import contextmanager
from enum import Enum, auto
from functools import reduce

class Context(Enum):
    Load = auto()
    Store = auto()

Load = Context.Load
Store = Context.Store


class Symbol:

    def __init__(self, name):
        self.name = name


class Global(Symbol):

    def __eq__(self, other):
        return other.__class__ is Global and self.name == other.name


class Free(Symbol):

    def __init__(self, name, parent):
        super().__init__(name)
        self.parent = parent

    def __eq__(self, other):
        return other.__class__ is Free and self.name == other.name and self.parent == other.parent


class Local(Symbol):
    is_referenced = False


class SymbolTable:

    def __init__(self, parent=None):
        self.parent = parent
        self.names = []
        self.table = {}
        self.symbols = []

    def get_name_slot(self, name):
        try:
            return self.names.index(name)
        except ValueError:
            slot = len(self.names)
            self.names.append(name)
            return slot

    def get_global(self, name):
        symbol = Global(name)
        symbol.slot = self.get_name_slot(name)
        return symbol

    def __contains__(self, name):
        if name in self.table:
            return True
        if self.parent:
            return name in self.parent
        return False

    def __getitem__(self, name):
        if name in self.table:
            return self.table[name]

        if self.parent is not None:
            if name in self.parent:
                symbol = self.parent[name]
                if isinstance(symbol, Local):
                    symbol.is_referenced = True
                symbol = Free(name, symbol)
                self.symbols.append(symbol)
                self.table[name] = symbol
                return symbol
        raise KeyError(name)

    def declare(self, name):
        if self.parent is not None:
            symbol = Local(name)
            self.symbols.append(symbol)
        else:
            symbol = self.get_global(name)
        return symbol

    def __setitem__(self, name, symbol):
        assert name not in self
        self.table[name] = symbol

    def get_slots(self):
        varnames = []
        freenames = []
        cellnames = []
        freevars = []
        for symbol in self.symbols:
            if isinstance(symbol, Free):
                if symbol not in freevars:
                    freevars.append(symbol)
            elif isinstance(symbol, Local):
                if symbol.is_referenced:
                    slot = len(cellnames)
                    cellnames.append(symbol.name)
                else:
                    slot = len(varnames)
                    varnames.append(symbol.name)
                symbol.slot = slot

        for symbol in self.symbols:
            if isinstance(symbol, Free):
                symbol.slot = len(cellvars) + freevars.index(symbol)

        return tuple(self.names), tuple(varnames), tuple(symbol.name for symbol in freevars), tuple(cellnames), tuple(freevars)


class BlockSymbolTable:

    def __init__(self, parent):
        self.parent = parent
        self.table = {}

    def get_name_slot(self, name):
        return self.parent.get_name_slot(name)

    def get_global(self, name):
        return self.parent.get_global(name)

    def __contains__(self, name):
        if name in self.table:
            return True
        return name in self.parent

    def __getitem__(self, name):
        if name in self.table:
            return self.table[name]
        return self.parent[name]

    def declare(self, name):
        return self.parent.declare(name)

    def __setitem__(self, name, symbol):
        assert name not in self
        self.table[name] = symbol

class BlockScope:
    def __init__(self, parent, n):
        self.parent = parent
        self.table = {}
        self.children = tuple(BlockSymbolTable(self) for _ in range(n))

    def get_name_slot(self, name):
        return self.parent.get_name_slot(name)

    def get_global(self, name):
        return self.parent.get_global(name)

    def __contains__(self, name):
        return name in self.parent

    def __getitem__(self, name):
        return self.parent[name]

    def declare(self, name):
        if name in self.table:
            return self.table[name]
        symbol = self.parent.declare(name)
        self.table[name] = symbol
        return symbol

    def __enter__(self):
        return self.children

    def __exit__(self, exc_type, exc_value, traceback):
        for key in self.table:
            self.parent[key] = self.table[key]
