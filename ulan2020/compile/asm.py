from types import CodeType
from dis import opmap
from .bytecode import COMPILER_FLAGS, Instruction, LineNumber, Label, resolve_offsets, encode_code, encode_lnotab


class Assembler:

    def __init__(self):
        self.insts = []
        self.constants = []
        self._stacksize = 0
        self.max_stacksize = 0

    def build(self, argcount, flags, names, varnames, filename, name, firstlineno, freevars, cellvars):
        # flags = self.CO_VARARGS | self.CO_NEWLOCALS
        flags |= self.CO_OPTIMIZED
        if not freevars and not cellvars:
            flags |= self.CO_NOFREE
        elif freevars:
            flags |= self.CO_NESTED

        resolve_offsets(self.insts)
        lnotab = bytes(encode_lnotab(self.insts, firstlineno))
        code = bytes(encode_code(self.insts))

        return CodeType(
            argcount,
            0,
            len(varnames) + len(cellvars),
            self.max_stacksize,
            flags,
            code,
            tuple(self.constants),
            names,
            varnames,
            filename,
            name,
            firstlineno,
            lnotab,
            freevars,
            cellvars)

    def emit(self, inst):
        inst.assign_constant_slot(self.constants)
        self.stacksize = inst.apply_stack_effect(self.stacksize)
        self.insts.append(inst)

    def set_lineno(self, node):
        self.emit(LineNumber(node.lineno))

    def __getattribute__(self, name):
        if name in opmap:
            def emit(arg=0):
                self.emit(Instruction(opmap[name], arg))
            return emit
        if name in COMPILER_FLAGS:
            return COMPILER_FLAGS[name]
        return super().__getattribute__(name)


    @property
    def stacksize(self):
        return self._stacksize

    @stacksize.setter
    def stacksize(self, value):
        self._stacksize = value
        self.max_stacksize = max(self.max_stacksize, value or 0)
