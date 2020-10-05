from .visit import Visitor
from .symbol import Symbol, SymbolTable, BlockScope, Local, Global, Load, Store
from . import ast

class ScopeVisitor(Visitor):

    @_(list)
    def visit(self, node, symtable):
        for subnode in node:
            yield from self.visit(subnode, symtable)

    @_(ast.File)
    def visit(self, node, symtable):
        scopes = list(self.visit(node.body, symtable))
        for scope in scopes:
            self.visit_scope(scope, symtable)
        node.symtable = symtable

    @_(ast.If)
    def visit(self, node, symtable):
        with BlockScope(symtable, 2) as (symtable1, symtable2):
            yield from self.visit(node.test, symtable1)
            yield from self.visit(node.body, symtable1)
            yield from self.visit(node.orelse, symtable2)

    @_(ast.Return)
    def visit(self, node, symtable):
        yield from self.visit(node.value, symtable)

    @_(ast.Arguments)
    def visit(self, node, symtable):
        for pat in node.args:
            yield from self.visit(pat.value, symtable)
        if node.vararg is not None:
            yield from self.visit(node.vararg, symtable)
        for pat in node.kwonlyargs:
            yield from self.visit(pat.value, symtable)
        if node.kwarg is not None:
            yield from self.visit(node.kwarg, symtable)

    @_(ast.Function)
    def visit(self, node, symtable):
        for pat in node.args.args:
            if getattr(pat, 'default', None) is not None:
                yield from self.visit(pat.default, symtable)
        for pat in node.args.kwonlyargs:
            if getattr(pat, 'default', None) is not None:
                yield from self.visit(pat.default, symtable)

        self.visit_new(node.name, symtable)
        yield node

    @_(ast.Call)
    def visit(self, node, symtable):
        yield from self.visit(node.func, symtable)
        yield from self.visit(node.args, symtable)
        yield from self.visit(node.keywords, symtable)

    @_(ast.Module)
    def visit(self, node, symtable):
        node.slot = symtable.get_name_slot(".".join(node.path))
        if False:
            yield

    @_(ast.ModuleAttribute)
    def visit(self, node, symtable):
        yield from self.visit(node.value, symtable)
        node.slot = symtable.get_name_slot(node.identifier)

    @_(ast.Literal)
    def visit(self, node, symtable):
        if False:
            yield

    @_(ast.Name)
    def visit(self, node, symtable):
        node.symbol = symtable[node.s]
        if False:
            yield

    @_(ast.Keyword)
    def visit(self, node, symtable):
        yield from self.visit(node.value, symtable)

    @_(ast.Match)
    def visit(self, node, symtable):
        node.slot = symtable.get_name_slot("__umatch__")
        node.exc = symtable.get_global(".MatchException")
        yield from self.visit(node.pattern, symtable)
        yield from self.visit(node.value, symtable)

    @_(ast.LiteralPattern)
    def visit(self, node, symtable):
        node.pat = symtable.get_global(".value")
        if False:
            yield

    @_(ast.NamePattern)
    def visit(self, node, symtable):
        if node.s in symtable:
            node.ctx = Load
            node.symbol = symtable[node.s]

            if isinstance(node.symbol, Global):
                node.pat = symtable.get_global(".gvar")
                node.globals = symtable.get_global(".globals")
            elif isinstance(node.symbol, Local):
                node.pat = symtable.get_global(".var")
                node.symbol.is_referenced = True
            else:
                node.pat = symtable.get_global(".value")
                return
        else:
            node.ctx = Store
            node.symbol = symtable.declare(node.s)
            symtable[node.s] = node.symbol

            if isinstance(node.symbol, Global):
                node.pat = symtable.get_global(".gnew")
                node.globals = symtable.get_global(".globals")
            else:
                node.pat = symtable.get_global(".new")
                node.symbol.is_referenced = True

        if False:
            yield

    @_(ast.Name)
    def visit_new(self, node, symtable):
        node.symbol = symtable.declare(node.s)
        symtable[node.s] = node.symbol

    @_(ast.Function)
    def visit_scope(self, node, symtable):
        node.symtable = SymbolTable(symtable)
        node.slot = node.symtable.get_name_slot("__umatch__")
        node.exc = node.symtable.get_global(".MatchException")

        scopes = []
        for pat in node.args.args:
            pat.symbol = Local(pat.arg)
            node.symtable.symbols.append(pat.symbol)
        if node.args.vararg is not None:
            symbol = Local("*")
            node.symtable.symbols.append(symbol)
            node.vararg = symbol
        for pat in node.args.kwonlyargs:
            pat.symbol = Local(pat.arg)
            node.symtable.symbols.append(pat.symbol)
        if node.args.kwarg is not None:
            symbol = Local("**")
            node.symtable.symbols.append(symbol)
            node.kwarg = symbol

        scopes.extend(self.visit(node.args, node.symtable))
        scopes.extend(self.visit(node.body, node.symtable))
        for scope in scopes:
            self.visit_scope(scope, symtable)
