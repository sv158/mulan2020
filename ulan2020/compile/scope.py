from .visit import Visitor
from .symbol import Symbol, SymbolTable
from . import ast

class ScopeVisitor(Visitor):

    @_(list)
    def visit(self, node, symtable):
        for subnode in node:
            yield from self.visit(subnode, symtable)

    @_(ast.File)
    def visit(self, node):
        symtable = SymbolTable()
        for scope in self.visit(node.body, symtable):
            self.visit_scope(scope, symtable)
        node.symtable = symtable

    @_(ast.If)
    def visit(self, node, symtable):
        yield from self.visit(node.test, symtable)
        yield from self.visit(node.body, symtable)
        yield from self.visit(node.orelse, symtable)

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
