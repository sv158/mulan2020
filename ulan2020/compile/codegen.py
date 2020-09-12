import os
from .visit import Visitor
from .asm import Assembler
from . import ast

class CodegenVisitor(Visitor):

    @_(list)
    def visit(self, node, asm):
        for subnode in node:
            self.visit(subnode, asm)
            if isinstance(subnode, ast.Expression):
                asm.POP_TOP()

    @_(ast.File)
    def visit(self, node):
        asm = Assembler()
        self.visit(node.body, asm)

        asm.LOAD_CONST(None)
        asm.RETURN_VALUE()

        names, varnames, freenames, cellnames, freevars = node.symtable.get_slots()

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
