from dis import opmap, opname, COMPILER_FLAG_NAMES, hasconst, hasjabs, hasjrel, HAVE_ARGUMENT, stack_effect

COMPILER_FLAGS = {f"CO_{v}":k for k, v in COMPILER_FLAG_NAMES.items()}

def extended_length(n):
    count = 0
    while n > 0:
        n >>= 8
        count += 1
    return count


_stack_effects = {
    opmap["BREAK_LOOP"]: (0, None, 0),
    opmap["CONTINUE_LOOP"]: (0, None, 0),
    opmap["JUMP_ABSOLUTE"]: (0, None, 0),
    opmap["JUMP_FORWARD"]: (0, None, 0),
    opmap["JUMP_IF_FALSE_OR_POP"]: (1, -1, 0),
    opmap["JUMP_IF_TRUE_OR_POP"]: (1, -1, 0),
    opmap["POP_JUMP_IF_FALSE"]: (1, -1, -1),
    opmap["POP_JUMP_IF_TRUE"]: (1, -1, -1),
    opmap["SETUP_EXCEPT"]: (0, 0, 3),
    opmap["RETURN_VALUE"]: (1, None,),
    opmap["RAISE_VARARGS"]: None
}

def _stack_effect(op, arg):
    effect = _stack_effects[op]
    if effect is not None:
        return effect
    if op == opmap["RAISE_VARARGS"]:
        return (arg, None)
    raise NotImplementedError

class Instruction:
    offset = 0

    def __init__(self, opcode, arg):
        self._op = opcode
        self._arg = arg

    def __repr__(self):
        return '{}({})'.format(opname[self._op], self._arg)

    @property
    def arg(self):
        if self._op in hasjabs:
            return self._arg.offset
        elif self._op in hasjrel:
            arg = self._arg.offset - self.offset
            if arg < 0:
                return 0
            length = 2 * (extended_length(arg >> 8) + 1)
            arg -= length
            return 0 if arg < 0 else arg
        elif self._op in hasconst:
            return self.slot
        elif self._op < HAVE_ARGUMENT:
            return 0
        else:
            return self._arg

    def __len__(self):
        return 2 * (extended_length(self.arg >> 8) + 1)

    def __iter__(self):
        length = len(self) // 2
        if length == 0:
            return
        arg = self.arg
        for i in range(length, 1, -1):
            yield opmap["EXTENDED_ARG"]
            yield (arg >> 8 * i) & 0xFF
        yield self._op
        yield arg & 0xFF

    def assign_constant_slot(self, consts):
        if not self._op in hasconst:
            return
        for i, c in enumerate(consts):
            if self._arg is c:
                self.slot = i
                return
        self.slot = len(consts)
        consts.append(self._arg)

    def apply_stack_effect(self, stacksize):
        if self._op not in _stack_effects:
            assert stacksize is not None
            if self._op < HAVE_ARGUMENT:
                return stacksize + stack_effect(self._op)
            else:
                return stacksize + stack_effect(self._op, self.arg)
        effect = _stack_effect(self._op, self.arg)
        assert stacksize >= effect[0]
        if len(effect) > 2:
            self._arg.stacksize = stacksize + effect[2]
        return None if effect[1] is None else stacksize + effect[1]

class Label:
    offset = 0
    stacksize = None

    def __len__(self):
        return 0

    def __iter__(self):
        if False:
            yield

    def assign_constant_slot(self, consts):
        pass

    def apply_stack_effect(self, stacksize):
        if self.stacksize is None:
            self.stacksize = stacksize
        elif stacksize is not None:
            assert self.stacksize == stacksize
        return self.stacksize

class LineNumber:
    offset = 0

    def __init__(self, n):
        self.n = n

    def __len__(self):
        return 0

    def __iter__(self):
        if False:
            yield

    def assign_constant_slot(self, consts):
        pass

    def apply_stack_effect(self, stacksize):
        return stacksize

def resolve_offsets(insts):
    resolved = False
    while not resolved:
        resolved = True
        offset = 0
        for inst in insts:
            if inst.offset != offset:
                resolved = False
                inst.offset = offset
            offset += len(inst)

def encode_code(insts):
    for inst in insts:
        yield from inst

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

def encode_lnotab(insts, firstlineno):
    lastoffset = 0
    lastlineno = firstlineno

    for offset, lineno in iter_lnotab(insts, firstlineno):
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
