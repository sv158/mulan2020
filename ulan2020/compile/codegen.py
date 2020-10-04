import os
from .visit import Visitor
from .asm import Assembler, Label
from .symbol import Load, Store, Global, Free, Local
from . import ast

class CodegenVisitor(Visitor):

    def visit_symbol(self, symbol, asm, context):
        context = {Load: 'LOAD', Store: 'STORE'}[context]

        if isinstance(symbol, Local):
            scope = 'DEREF' if symbol.is_referenced else 'FAST'
        else:
            scope = {Global: 'GLOBAL', Free: 'DEREF'}[type(symbol)]

        getattr(asm, f'{context}_{scope}')(symbol.slot)


    @_(list)
    def visit(self, node, asm):
        for subnode in node:
            self.visit(subnode, asm)
            if isinstance(subnode, ast.Match):
                label = Label()
                asm.POP_JUMP_IF_TRUE(label)
                asm.LOAD_GLOBAL(subnode.exc.slot)
                asm.ROT_TWO()
                asm.CALL_FUNCTION(1)
                asm.RAISE_VARARGS(1)
                asm.emit(label)
                asm.POP_TOP()
            elif isinstance(subnode, ast.Expression):
                asm.POP_TOP()

    @_(ast.File)
    def visit(self, node):
        asm = Assembler()
        names, varnames, freenames, cellnames, freevars = node.symtable.get_slots()
        self.visit(node.body, asm)

        asm.LOAD_CONST(None)
        asm.RETURN_VALUE()

        flags = 0
        return asm.build(
            0,
            flags,
            names,
            varnames,
            self.filename,
            os.path.basename(self.filename),
            node.lineno,
            freenames,
            cellnames)

    @_(ast.If)
    def visit(self, node, asm):
        self.visit(node.test, asm)
        if isinstance(node.test, ast.Match):
            asm.ROT_TWO()
            asm.POP_TOP()

        label1 = Label()
        label2 = Label()
        asm.POP_JUMP_IF_FALSE(label1)
        self.visit(node.body, asm)
        asm.JUMP_FORWARD(label2)
        asm.emit(label1)
        self.visit(node.orelse, asm)
        asm.emit(label2)

    @_(ast.Call)
    def visit(self, node, asm):
        self.visit(node.func, asm)
        argcount = 0
        tuplecount = 0

        for arg in node.args:
            if isinstance(arg, ast.Unpack):
                if argcount:
                    asm.BUILD_TUPLE(argcount)
                    argcount = 0
                    tuplecount += 1
                self.visit(arg.value, asm)
                tuplecount += 1
            else:
                self.visit(arg, asm)
                argcount += 1

        if tuplecount:
            if argcount:
                asm.BUILD_TUPLE(argcount)
                argcount = 0
                tuplecount += 1
            asm.BUILD_TUPLE_UNPACK_WITH_CALL(tuplecount)
        elif any(isinstance(arg, ast.Unpack) for arg in node.keywords):
            asm.BUILD_TUPLE(argcount)
            argcount = 0
            tuplecount = 1

        kwds = ()
        mapcount = 0

        for arg in node.keywords:
            if isinstance(arg, ast.Unpack):
                if kwds:
                    asm.LOAD_CONST(kwds)
                    asm.BUILD_CONST_KEY_MAP(len(kwds))
                    kwds = ()
                    mapcount += 1
                self.visit(arg.value, asm)
                mapcount += 1
            else:
                kwds = kwds + (arg.arg,)
                self.visit(arg.value, asm)

        if mapcount or tuplecount:
            if kwds:
                asm.LOAD_CONST(kwds)
                asm.BUILD_CONST_KEY_MAP(len(kwds))
                kwds = ()
                mapcount += 1
        if mapcount:
            asm.BUILD_MAP_UNPACK_WITH_CALL(mapcount)
            asm.CALL_FUNCTION_EX(1)
        elif tuplecount:
            asm.CALL_FUNCTION_EX(0)
        elif kwds:
            asm.LOAD_CONST(kwds)
            asm.CALL_FUNCTION_KW(argcount + len(kwds))
        else:
            asm.CALL_FUNCTION(argcount)

    @_(ast.ModuleAttribute)
    def visit(self, node, asm):
        asm.LOAD_CONST(node.value.level)
        asm.LOAD_CONST((node.identifier,))
        asm.IMPORT_NAME(node.value.slot)
        asm.IMPORT_FROM(node.slot)
        asm.ROT_TWO()
        asm.POP_TOP()

    @_(ast.Literal)
    def visit(self, node, asm):
        asm.LOAD_CONST(node.value)

    @_(ast.Name)
    def visit(self, node, asm):
        self.visit_symbol(node.symbol, asm, Load)

    @_(ast.Match)
    def visit(self, node, asm):
        self.visit(node.pattern, asm)
        asm.LOAD_ATTR(node.slot)
        self.visit(node.value, asm)
        asm.DUP_TOP()
        asm.ROT_THREE()
        asm.CALL_FUNCTION(1)

    @_(ast.LiteralPattern)
    def visit(self, node, asm):
        asm.LOAD_GLOBAL(node.pat.slot)
        asm.LOAD_CONST(node.value)
        asm.CALL_FUNCTION(1)

    @_(ast.NamePattern)
    def visit(self, node, asm):
        asm.LOAD_GLOBAL(node.pat.slot)
        if isinstance(node.symbol, Local):
            assert node.symbol.is_referenced
            asm.LOAD_CLOSURE(node.symbol.slot)
            asm.CALL_FUNCTION(1)
        elif isinstance(node.symbol, Global):
            asm.LOAD_GLOBAL(node.globals.slot)
            asm.CALL_FUNCTION(0)
            asm.LOAD_CONST(node.s)
            asm.CALL_FUNCTION(2)
        else:
            self.visit_symbol(node.symbol, asm, node.ctx)
            asm.CALL_FUNCTION(1)
