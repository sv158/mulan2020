from enum import Enum
from dis import opmap, opname, COMPILER_FLAG_NAMES, hasconst, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect
from types import CodeType

COMPILER_FLAGS = {f"CO_{v}":k for k, v in COMPILER_FLAG_NAMES.items()}

class Instruction:
    offset = 0

    def __init__(self, opcode, arg):
        self.opcode = opcode
        self.arg = arg

    def __repr__(self):
        return '{}({})'.format(opname[self.opcode], self.arg)

class Label:
    offset = 0
    stacksize = None

class LineNumber:
    offset = 0

    def __init__(self, n):
        self.n = n


def extended_length(n):
    count = 0
    while n > 0:
        n >>= 8
        count += 1
    return count

def get_arg(inst, offset):
    if inst.opcode in hasjabs:
        return inst.arg.offset
    elif inst.opcode in hasjrel:
        arg = inst.arg.offset - offset
        if arg < 0:
            return 0
        length = 2 * (extended_length(arg >> 8) + 1)
        arg -= length
        return 0 if arg < 0 else arg
    elif inst.opcode in hasconst:
        return inst.slot
    else:
        return inst.arg

def length_of_inst(inst, offset):
    if not isinstance(inst, Instruction):
        return 0
    arg = get_arg(inst, offset)
    return 2 * (extended_length(arg >> 8) + 1)

def validate_offset(insts):
    offset = 0
    for inst in insts:
        if inst.offset != offset:
            return False
        offset += length_of_inst(inst, offset)
    return True

def assign_offset(insts):
    offset = 0
    for inst in insts:
        inst.offset = offset
        offset += length_of_inst(inst, offset)

def extend_arg(insts):
    for inst in insts:
        if not isinstance(inst, Instruction):
            continue
        arg = get_arg(inst, inst.offset)
        length = length_of_inst(inst, inst.offset)//2
        if length == 0:
            continue
        for i in range(length, 1, -1):
            yield Instruction(opmap["EXTENDED_ARG"], (arg >> 8 * i) & 0xFF)
        yield Instruction(inst.opcode, (arg & 0xFF))

def resolve_offsets(insts):
    while not validate_offset(insts):
        assign_offset(insts)

def assemble_code(insts):
    return b''.join(
        bytes([inst.opcode, inst.arg if inst.opcode >= HAVE_ARGUMENT else 0])
        for inst in extend_arg(insts))

def iter_lnotab(insts, firstlineno):
    last = firstlineno
    current = last

    for inst in insts:
        if isinstance(inst, LineNumber):
            current = inst.n
        else:
            if current != last:
                yield inst.offset, current
            last = current

def iter_line_incr(line_incr):
    if line_incr > 0:
        while line_incr > 127:
            line_incr -= 127
            yield 127
        yield line_incr
    else:
        while line_incr < -128:
            line_incr += 128
            yield 128
        yield 256 + line_incr

def encode_lnotab(lnotab, firstlineno):
    lastoffset = 0
    lastlineno = firstlineno

    for offset, lineno in lnotab:
        line_incr = lineno - lastlineno
        if line_incr == 0:
            continue
        byte_incr = offset - lastoffset

        while byte_incr > 255:
            byte_incr -= 255
            yield 255
            yield 0

        it = iter_line_incr(line_incr)
        yield byte_incr
        yield next(it)
        for i in it:
            yield 0
            yield i

        lastoffset = offset
        lastlineno = lineno

def assemble_lnotab(insts, firstlineno):
    return bytes(encode_lnotab(iter_lnotab(insts, firstlineno), firstlineno))

class Assembler:

    def __init__(self):
        self.insts = []
        self.constants = []
        self._stacksize = 0
        self.max_stacksize = 0

    def get_constant_slot(self, const):
        for i, c in enumerate(self.constants):
            if const is c:
                return i

        slot = len(self.constants)
        self.constants.append(const)
        return slot

    def build(self, argcount, flags, names, varnames, filename, name, firstlineno, freevars, cellvars):
        # flags = self.CO_VARARGS | self.CO_NEWLOCALS
        flags |= self.CO_OPTIMIZED
        if not freevars and not cellvars:
            flags |= self.CO_NOFREE
        elif freevars:
            flags |= self.CO_NESTED

        resolve_offsets(self.insts)
        lnotab = assemble_lnotab(self.insts, firstlineno)
        code = assemble_code(self.insts)

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
        if isinstance(inst, Instruction):
            op = inst.opcode
            if op in hasconst:
                slot = self.get_constant_slot(inst.arg)
                inst.slot = slot
                self.stacksize += stack_effect(op, slot)
            elif op < HAVE_ARGUMENT:
                self.stacksize += stack_effect(op)
            else:
                self.stacksize += stack_effect(op, inst.arg)

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
        return object.__getattribute__(self, name)


    @property
    def stacksize(self):
        return self._stacksize

    @stacksize.setter
    def stacksize(self, value):
        self._stacksize = value
        self.max_stacksize = max(self.max_stacksize, value)
