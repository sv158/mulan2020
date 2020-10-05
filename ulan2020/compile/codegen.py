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

        flags = 0
        return asm.build(
            0,
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

    @_(ast.Return)
    def visit(self, node, asm):
        self.visit(node.value, asm)
        asm.RETURN_VALUE()

    def visit_function(self, node, name, asm):
        names, varnames, freenames, cellnames, freevars = node.symtable.get_slots()
        sub = Assembler()

        flags = 0

        label_exc = Label()
        label_body = Label()

        for pat in node.args.args:
            self.visit(pat.value, sub)
            sub.LOAD_ATTR(node.slot)
            sub.LOAD_FAST(pat.symbol.slot)
            sub.CALL_FUNCTION(1)
            sub.POP_JUMP_IF_FALSE(label_exc)

        if node.args.vararg is not None:
            flags |= sub.CO_VARARGS
            self.visit(node.args.vararg, sub)
            sub.LOAD_ATTR(node.slot)
            sub.LOAD_FAST(node.vararg.slot)
            sub.CALL_FUNCTION(1)
            sub.POP_JUMP_IF_FALSE(label_exc)

        for pat in node.args.kwonlyargs:
            self.visit(pat.value, sub)
            sub.LOAD_ATTR(node.slot)
            sub.LOAD_FAST(pat.symbol.slot)
            sub.CALL_FUNCTION(1)
            sub.POP_JUMP_IF_FALSE(label_exc)

        if node.args.kwarg is not None:
            flags |= sub.CO_VARKEYWORDS
            self.visit(node.args.kwarg, sub)
            sub.LOAD_ATTR(node.slot)
            sub.LOAD_FAST(node.kwarg.slot)
            sub.CALL_FUNCTION(1)
            sub.POP_JUMP_IF_FALSE(label_exc)

        if label_exc.stacksize is not None:
            sub.JUMP_FORWARD(label_body)
            sub.emit(label_exc)
            sub.LOAD_GLOBAL(node.exc.slot)
            for pat in node.args.args:
                sub.LOAD_FAST(pat.symbol.slot)
            sub.BUILD_TUPLE(len(node.args.args))
            if node.args.vararg is not None:
                sub.LOAD_FAST(node.vararg.slot)
                sub.BUILD_TUPLE_UNPACK(2)
            if node.args.kwonlyargs:
                for pat in node.args.kwonlyargs:
                    sub.LOAD_FAST(pat.symbol.slot)
                sub.LOAD_CONST(tuple(pat.arg for pat in node.args.kwonlyargs))
                sub.BUILD_CONST_KEY_MAP(len(node.args.kwonlyargs))
                if node.args.kwarg:
                    sub.LOAD_FAST(node.kwarg.slot)
                    sub.BUILD_MAP_UNPACK(2)
                sub.BUILD_TUPLE(2)
            elif node.args.kwarg:
                sub.LOAD_FAST(node.kwarg.slot)
                sub.BUILD_TUPLE(2)
            sub.CALL_FUNCTION(1)
            sub.RAISE_VARARGS(1)
            sub.emit(label_body)

        self.visit(node.body, sub)

        code = sub.build(
            len(node.args.args),
            len(node.args.kwonlyargs),
            flags,
            names,
            varnames,
            self.filename,
            os.path.basename(self.filename),
            node.lineno,
            freenames,
            cellnames)

        flags = 0

        defaults = [pat.default for pat in node.args.args if getattr(pat, 'default', None) is not None]
        if defaults:
            for default in defaults:
                self.visit(default, asm)
            asm.BUILD_TUPLE(len(defaults))
            flags |= 0x01

        defaults = [pat for pat in node.args.kwonlyargs if getattr(pat, 'default', None) is not None]
        if defaults:
            for pat in defaults:
                self.visit(pat.default, asm)
            asm.LOAD_CONST(tuple(pat.arg for pat in defaults))
            asm.BUILD_CONST_KEY_MAP(len(defaults))
            flags |= 0x02

        if freevars:
            for freevar in freevars:
                asm.LOAD_CLOSURE(freevar.parent.slot)
            asm.BUILD_TUPLE(len(freevars))
            flags |= 0x08

        asm.LOAD_CONST(code)
        asm.LOAD_CONST(name)
        asm.MAKE_FUNCTION(flags)

    @_(ast.Function)
    def visit(self, node, asm):
        self.visit_function(node, node.name.s, asm)
        self.visit_symbol(node.name.symbol, asm, Store)

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
