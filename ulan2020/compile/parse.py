import re
import typing
import sly
from sly.yacc import YaccSymbol, YaccProduction
from .error import Error

def position(p):
    if isinstance(p, YaccSymbol):
        return position(p.value)
    elif isinstance(p, YaccProduction):
        return position(p._slice[0])
    elif isinstance(p, list):
        return position(p[0])
    return p


class Node:

    def __init__(self, *args, **kwargs):
        if args:
            p = position(args[0])
            self.lineno = p.lineno
            self.index = p.index
        self.__dict__.update(kwargs)

    def __str__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            ", ".join(
                f"{key}={getattr(self, key)}"
                for key in self.__class__.__annotations__
                if hasattr(self, key))
        )


class Statement(Node):
    pass

class Condition(Statement):
    pass

class File(Node):
    body: typing.List[Statement]

class Expression(Condition):
    pass

class Name(Expression):
    s: str

class Unpack(Node):
    value: Expression

class Arguments(Node):
    args: typing.List[Expression]
    vararg: typing.Optional[Unpack]
    kwonlyargs: typing.List[Expression]
    kwarg: typing.Optional[Unpack]

class Function(Statement):
    name: Name
    args: Arguments
    body: typing.List[Statement]

class If(Statement):
    test: Condition
    body: typing.List[Statement]
    orelse: typing.List[Statement]

class Return(Statement):
    value: Expression

class Match(Condition):
    pattern: Expression
    value: Expression

class Submodule(Expression):
    parent: typing.Optional[Expression]
    name: str

class Subscript(Expression):
    value: Expression
    slice: Expression

class Attribute(Expression):
    value: Expression
    identifier: str

class Keyword(Expression):
    arg: str
    value: Expression
    default: typing.Optional[Expression]

class Tuple(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class List(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class Set(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class Field(Node):
    key: Expression
    value: Expression
    default: typing.Optional[Expression]

class Dict(Expression):
    elts: typing.List[typing.Union[Field, Unpack]]

class Call(Expression):
    func: Expression
    args: typing.List[typing.Union[Expression, Unpack]]
    keywords: typing.List[typing.Union[Keyword, Unpack]]

class BinOp(Expression):
    left: Expression
    op: typing.Union[Expression, str]
    right: Expression

class Literal(Expression):
    value: typing.Union[int, float, str]

class UnaryOp(Expression):
    op: typing.Union[Expression, str]
    operand: Expression


class Lexer(Error, sly.Lexer):
    reflags = re.UNICODE

    tokens = {
        ATTRIBUTE,
        DEC,
        DEF,
        ELSE,
        END,
        FLOAT,
        HEX,
        IF,
        IS,
        LET,
        MAP_UNPACK,
        MODULE,
        NAME,
        OCT,
        RETURN,
        STRING,
        STRIP_STRING,
    }

    literals = {";", ",", ".", ":", "_", "(", ")", "=", "[", "]", "{", "}", "|", "*", "/"}


    ATTRIBUTE = r'->'
    DEC = r'[0-9]+'
    FLOAT = r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    HEX = r'0x[0-9A-Fa-f]+'
    OCT = r'0o[0-7]+'
    MAP_UNPACK = r'\*\*'
    MODULE = r'\:\:'

    NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
    NAME['def'] = DEF
    NAME['else'] = ELSE
    NAME['end'] = END
    NAME['if'] = IF
    NAME['is'] = IS
    NAME['let'] = LET
    NAME['return'] = RETURN

    ignore = ' \t'

    @_(r'{(?P<b>=*)\[(?:(?!\](?P=b)}).|\n)*\](?P=b)}')
    def STRING(self, t):
        self.lineno += t.value.count('\n')
        p = t.value.find('[')
        value = t.value[p+1:t.value.rfind(']')]

        if p > 1:
            p = value.find("\n")
            if p >= 0 and not value[:p].strip():
                value = value[p+1:]
            p = value.rfind("\n")
            if p >= 0 and not value[p:].strip():
                value = value[:p]
        t.value = value
        return t

    @_(r'{(?P<c>-+)\[(?:(?!\](?P=c)}).|\n)*\](?P=c)}')
    def STRIP_STRING(self, t):
        self.lineno += t.value.count('\n')
        t.value = t.value[t.value.find('[')+1:t.value.rfind(']')].strip()
        return t

    ignore_comment = r'#[^\n]*(?=\n|$)'

    @_(r'\n+')
    def ignore_NEWLINE(self, t):
        self.lineno += len(t.value)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def error(self, t):
        super().error(t, f"Bad character {t.value[0]!r}")



class Parser(Error, sly.Parser):
    # debugfile = 'parser.out'
    tokens = Lexer.tokens

    def __init__(self, filename, text):
        super().__init__()
        self.filename = filename
        self.text = text

    def error(self, t):
        if t is None:
            raise EOFError()
        super().error(t, f"Invalid token {t.value!r}")

    def position(self, p, i=None):
        if i is None:
            return self._position(p)
        return self._position(p._slice[i])

    @_('block')
    def file(self, p):
        if p[0]:
            return File(p, body=p[0])
        node = File(body=[])
        node.lineno = 1
        node.index = 0
        return node

    @_('stat block')
    def block(self, p):
        return [p[0]] + p[1]

    @_('')
    def block(self, p):
        return []

    @_('condition ";"',
       'function')
    def stat(self, p):
        return p[0]

    @_('RETURN exp ";"')
    def stat(self, p):
        return Return(p, value=p[1])

    @_('RETURN ";"')
    def stat(self, p):
        return Return(p, value=Literal(p, value=None))

    @_('IF condition ":" block ifstat')
    def stat(self, p):
        return If(
            p,
            test=p[1],
            body=p[3],
            orelse=p[4])

    @_('ELSE IF condition ":" block ifstat')
    def ifstat(self, p):
        return [
            If(
                p,
                test=p[2],
                body=p[4],
                orelse=p[5])]

    @_('ELSE ":" block END')
    def ifstat(self, p):
        return p[2]

    @_('END')
    def ifstat(self, p):
        return []

    @_('binop',
       'unop',
       'is_exp_and_pat',
       'prefixexp',
       'match')
    def condition(self, p):
        return p[0]

    @_('exp_and_pat',
       'exp_not_pat')
    def exp(self, p):
       return p[0]

    @_('exp_and_pat',
       'pat_not_exp')
    def pat(self, p):
        return p[0]

    @_('prefixexp_exp_and_pat',
       'is_exp_and_pat')
    def exp_and_pat(self, p):
        return p[0]

    @_('prefixexp_exp_and_pat IS prefixexp_exp_and_pat')
    def is_exp_and_pat(self, p):
        return BinOp(p, left=p[0], op="is", right=p[2])

    @_('prefixexp_exp_not_pat',
       'binop',
       'unop')
    def exp_not_pat(self, p):
        return p[0]

    @_('is_exp_and_pat IS prefixexp_exp_and_pat',
       'is_exp_and_pat IS is_pat_not_exp',
       'pat_not_exp IS prefixexp_exp_and_pat',
       'pat_not_exp IS is_pat_not_exp')
    def pat_not_exp(self, p):
        return BinOp(p, left=p[0], op="is", right=p[2])

    @_('is_pat_not_exp')
    def pat_not_exp(self, p):
        return p[0]

    @_('list_pat_not_exp',
       'set_pat_not_exp',
       'dict_pat_not_exp',
       'call_pat_not_exp')
    def is_pat_not_exp(self, p):
        return p[0]

    @_('"(" tuple_pat_not_exp ")"')
    def is_pat_not_exp(self, p):
        return Tuple(p, elts=p[1])

    @_('prefixexp "." prefixexp "." prefixexp')
    def binop(self, p):
       return BinOp(p, left=p[0], op=p[2], right=p[4])

    @_('"." prefixexp "." prefixexp')
    def unop(self, p):
       return UnaryOp(p, op=p[1], operand=p[3])

    @_('prefixexp_exp_and_pat',
       'prefixexp_exp_not_pat')
    def prefixexp(self, p):
        return p[0]

    @_('tuple_exp_and_pat',
       'tuple_exp_not_pat')
    def tuple_exp(self, p):
        return Tuple(p, elts=p[0])

    @_('literal',
       'name',
       'list_exp_and_pat',
       'set_exp_and_pat',
       'dict_exp_and_pat',
       'call_exp_and_pat')
    def prefixexp_exp_and_pat(self, p):
        return p[0]

    @_('"(" empty ")"',
       '"(" tuple_exp_and_pat ")"')
    def prefixexp_exp_and_pat(self, p):
        return Tuple(p, elts=p[1])

    @_('module',
       'modattr',
       'subscript',
       'attribute',
       'paren',
       'list_exp_not_pat',
       'set_exp_not_pat',
       'dict_exp_not_pat',
       'call_exp_not_pat'
       )
    def prefixexp_exp_not_pat(self, p):
        return p[0]

    @_('"(" tuple_exp_not_pat ")"')
    def prefixexp_exp_not_pat(self, p):
        return Tuple(p, elts=p[1])


    @_('tuple_unpack_exp_and_pat')
    def tuple_exp_and_pat(self, p):
        return [p[0]]

    @_('exp_and_pat "," tuple_args_exp_and_pat',
       'exp_and_pat "," empty')
    def tuple_exp_and_pat(self, p):
        return [p[0]] + p[2]

    @_('tuple_unpack_exp_not_pat')
    def tuple_exp_not_pat(self, p):
        return [p[0]]

    @_('exp_and_pat "," tuple_args_exp_not_pat',
       'exp_not_pat "," tuple_args_exp_and_pat',
       'exp_not_pat "," tuple_args_exp_not_pat',
       'exp_not_pat "," empty')
    def tuple_exp_not_pat(self, p):
        return [p[0]] + p[2]

    @_('tuple_unpack_pat_not_exp')
    def tuple_pat_not_exp(self, p):
        return [p[0]]

    @_('exp_and_pat "," tuple_args_pat_not_exp',
       'pat_not_exp "," tuple_args_exp_and_pat',
       'pat_not_exp "," tuple_args_pat_not_exp',
       'pat_not_exp "," empty')
    def tuple_pat_not_exp(self, p):
        return [p[0]] + p[2]

    @_('tuple_args_exp_and_pat "," tuple_arg_exp_and_pat')
    def tuple_args_exp_and_pat(self, p):
        return p[0] + [p[2]]

    @_('tuple_arg_exp_and_pat')
    def tuple_args_exp_and_pat(self, p):
        return [p[0]]

    @_('exp_and_pat',
       'tuple_unpack_exp_and_pat')
    def tuple_arg_exp_and_pat(self, p):
        return p[0]

    @_('tuple_args_exp_and_pat "," tuple_arg_exp_not_pat',
       'tuple_args_exp_not_pat "," tuple_arg_exp_and_pat',
       'tuple_args_exp_not_pat "," tuple_arg_exp_not_pat')
    def tuple_args_exp_not_pat(self, p):
        return p[0] + [p[2]]

    @_('tuple_arg_exp_not_pat')
    def tuple_args_exp_not_pat(self, p):
        return [p[0]]

    @_('exp_not_pat',
       'tuple_unpack_exp_not_pat')
    def tuple_arg_exp_not_pat(self, p):
        return p[0]

    @_('tuple_args_exp_and_pat "," tuple_arg_pat_not_exp',
       'tuple_args_pat_not_exp "," tuple_arg_exp_and_pat',
       'tuple_args_pat_not_exp "," tuple_arg_pat_not_exp')
    def tuple_args_pat_not_exp(self, p):
        return p[0] + [p[2]]

    @_('tuple_arg_pat_not_exp')
    def tuple_args_exp_not_pat(self, p):
        return [p[0]]

    @_('pat_not_exp',
       'tuple_unpack_pat_not_exp')
    def tuple_arg_pat_not_exp(self, p):
        return p[0]

    @_('"*" exp_and_pat')
    def tuple_unpack_exp_and_pat(self, p):
       return Unpack(p, value=p[1])

    @_('"*" exp_not_pat')
    def tuple_unpack_exp_not_pat(self, p):
       return Unpack(p, value=p[1])

    @_('"*" pat_not_exp')
    def tuple_unpack_pat_not_exp(self, p):
       return Unpack(p, value=p[1])

    @_('float',
       'int',
       'string')
    def literal(self, p):
        return p[0]

    @_('FLOAT')
    def float(self, p):
        return Literal(p, value=float(p[0]))

    @_('DEC',
       'OCT',
       'HEX')
    def int(self, p):
        return Literal(p, value=int(p[0]))

    @_('STRING',
       'STRIP_STRING')
    def string(self, p):
        return Literal(p, value=p[0])

    @_('NAME')
    def name(self, p):
        return Name(p, s=p[0])

    @_('NAME MODULE')
    def module(self, p):
        return Submodule(p, parent=None, name=p[0])

    @_('MODULE')
    def module(self, p):
        return Submodule(p, parent=None, name='')

    @_('module NAME MODULE')
    def module(self, p):
        return Submodule(p, parent=p[0], name=p[1])

    @_('module NAME')
    def modattr(self, p):
        return Attribute(p, value=p[0], identifier=p[1])

    @_('prefixexp "[" tuple_exp "]"',
       'prefixexp "[" exp "]"')
    def subscript(self, p):
        return Subscript(p, value=p[0], slice=p[2])

    @_('prefixexp ATTRIBUTE NAME')
    def attribute(self, p):
        return Attribute(p, value=p[0], identifier=p[2])

    @_('"(" exp ")"')
    def paren(self, p):
       return p[1]

    @_('"[" tuple_args_exp_and_pat "]"',
       '"[" empty "]"')
    def list_exp_and_pat(self, p):
        return List(p, elts=p[1])

    @_('"[" tuple_args_exp_not_pat "]"')
    def list_exp_not_pat(self, p):
        return List(p, elts=p[1])

    @_('"[" tuple_args_pat_not_exp "]"')
    def list_pat_not_exp(self, p):
        return List(p, elts=p[1])

    @_('"{" "/" "}"',
    '"{" tuple_args_exp_and_pat "}"')
    def set_exp_and_pat(self, p):
        return Set(p, elts=[])

    @_('"{" tuple_args_exp_not_pat "}"')
    def set_exp_not_pat(self, p):
        return Set(p, elts=p[1])

    @_('"{" tuple_args_pat_not_exp "}"')
    def set_pat_not_exp(self, p):
        return Set(p, elts=p[1])

    @_('"{" empty "}"',
       '"{" dict_fields_exp_and_pat "}"')
    def dict_exp_and_pat(self, p):
        return Dict(p, elts=p[1])

    @_('"{" dict_fields_exp_not_pat "}"')
    def dict_exp_not_pat(self, p):
        return Dict(p, elts=p[1])

    @_('"{" dict_fields_pat_not_exp "}"')
    def dict_pat_not_exp(self, p):
        return Dict(p, elts=p[1])

    @_('dict_fields_exp_and_pat "," dict_field_exp_and_pat')
    def dict_fields_exp_and_pat(self, p):
        return p[0] + [p[2]]

    @_('dict_field_exp_and_pat')
    def dict_fields_exp_and_pat(self, p):
        return [p[0]]

    @_('exp ":" exp_and_pat')
    def dict_field_exp_and_pat(self, p):
        return Field(p, key=p[0], value=p[2])

    @_('map_unpack_exp_and_pat')
    def dict_field_exp_and_pat(self, p):
        return p[0]

    @_('dict_fields_exp_and_pat "," dict_field_exp_not_pat',
       'dict_fields_exp_not_pat "," dict_field_exp_and_pat',
       'dict_fields_exp_not_pat "," dict_field_exp_not_pat')
    def dict_fields_exp_not_pat(self, p):
        return p[0] + [p[2]]

    @_('dict_field_exp_not_pat')
    def dict_fields_exp_not_pat(self, p):
        return [p[0]]

    @_('exp ":" exp_not_pat')
    def dict_field_exp_not_pat(self, p):
        return Field(p, key=p[0], value=p[2])

    @_('map_unpack_exp_not_pat')
    def dict_field_exp_not_pat(self, p):
        return p[0]

    @_('dict_fields_exp_and_pat "," dict_field_pat_not_exp',
       'dict_fields_pat_not_exp "," dict_field_exp_and_pat',
       'dict_fields_pat_not_exp "," dict_field_pat_not_exp')
    def dict_fields_pat_not_exp(self, p):
        return p[0] + [p[2]]

    @_('dict_field_pat_not_exp')
    def dict_fields_pat_not_exp(self, p):
        return [p[0]]

    @_('exp ":" pat_not_exp')
    def dict_field_pat_not_exp(self, p):
        return Field(p, key=p[0], value=p[2])

    @_('exp ":" exp_and_pat "=" exp',
       'exp ":" exp_not_pat "=" exp')
    def dict_field_pat_not_exp(self, p):
        return Field(p, key=p[0], value=p[2], default=p[4])

    @_('map_unpack_pat_not_exp')
    def dict_field_pat_not_exp(self, p):
        return p[0]

    @_('MAP_UNPACK exp_and_pat')
    def map_unpack_exp_and_pat(self, p):
        return Unpack(p, value=p[1])

    @_('MAP_UNPACK exp_not_pat')
    def map_unpack_exp_not_pat(self, p):
        return Unpack(p, value=p[1])

    @_('MAP_UNPACK pat_not_exp')
    def map_unpack_pat_not_exp(self, p):
        return Unpack(p, value=p[1])

    @_('prefixexp "(" tuple_args_exp_and_pat "," keywords_exp_and_pat ")"')
    def call_exp_and_pat(self, p):
        return Call(p, func=p[0], args=p[2], keywords=p[4])

    @_('prefixexp "(" tuple_args_exp_and_pat "," keywords_exp_not_pat ")"',
       'prefixexp "(" tuple_args_exp_not_pat "," keywords_exp_and_pat ")"',
       'prefixexp "(" tuple_args_exp_not_pat "," keywords_exp_not_pat ")"')
    def call_exp_not_pat(self, p):
        return Call(p, func=p[0], args=p[2], keywords=p[4])

    @_('prefixexp "(" tuple_args_exp_and_pat "," keywords_pat_not_exp ")"',
       'prefixexp "(" tuple_args_pat_not_exp "," keywords_exp_and_pat ")"',
       'prefixexp "(" tuple_args_pat_not_exp "," keywords_pat_not_exp ")"')
    def call_pat_not_exp(self, p):
        return Call(p, func=p[0], args=p[2], keywords=p[4])

    @_('prefixexp "(" tuple_args_exp_and_pat ")"',
       'prefixexp "(" empty ")"')
    def call_exp_and_pat(self, p):
        return Call(p, func=p[0], args=p[2], keywords=[])

    @_('prefixexp "(" tuple_args_exp_not_pat ")"')
    def call_exp_not_pat(self, p):
        return Call(p, func=p[0], args=p[2], keywords=[])

    @_('prefixexp "(" tuple_args_pat_not_exp ")"')
    def call_pat_not_exp(self, p):
        return Call(p, func=p[0], args=p[2], keywords=[])

    @_('prefixexp "(" keywords_exp_and_pat ")"')
    def call_exp_and_pat(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('prefixexp "(" keywords_exp_not_pat ")"')
    def call_exp_not_pat(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('prefixexp "(" keywords_pat_not_exp ")"')
    def call_pat_not_exp(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('prefixexp "{" name_keywords_exp_and_pat "}"',
       'prefixexp "{" empty "}"')
    def call_exp_and_pat(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('prefixexp "{" name_keywords_exp_not_pat "}"')
    def call_exp_not_pat(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('prefixexp "{" name_keywords_pat_not_exp "}"')
    def call_pat_not_exp(self, p):
        return Call(p, func=p[0], args=[], keywords=p[2])

    @_('keywords_exp_and_pat "," keyword_exp_and_pat',
       'keywords_exp_and_pat "," tuple_unpack_exp_and_pat')
    def keywords_exp_and_pat(self, p):
        return p[0] + [p[2]]

    @_('keyword_exp_and_pat')
    def keywords_exp_and_pat(self, p):
        return [p[0]]

    @_('keywords_exp_and_pat "," keyword_exp_not_pat',
       'keywords_exp_not_pat "," keyword_exp_and_pat',
       'keywords_exp_not_pat "," keyword_exp_not_pat',
       'keywords_exp_and_pat "," tuple_unpack_exp_not_pat',
       'keywords_exp_not_pat "," tuple_unpack_exp_and_pat',
       'keywords_exp_not_pat "," tuple_unpack_exp_not_pat')
    def keywords_exp_not_pat(self, p):
        return p[0] + [p[2]]

    @_('keyword_exp_not_pat')
    def keywords_exp_not_pat(self, p):
        return [p[0]]

    @_('keywords_exp_and_pat "," keyword_pat_not_exp',
       'keywords_pat_not_exp "," keyword_exp_and_pat',
       'keywords_pat_not_exp "," keyword_pat_not_exp',
       'keywords_exp_and_pat "," tuple_unpack_pat_not_exp',
       'keywords_pat_not_exp "," tuple_unpack_exp_and_pat',
       'keywords_pat_not_exp "," tuple_unpack_pat_not_exp')
    def keywords_pat_not_exp(self, p):
        return p[0] + [p[2]]

    @_('keyword_pat_not_exp')
    def keywords_pat_not_exp(self, p):
        return [p[0]]

    @_('NAME ":" exp_and_pat',
       'END ":" exp_and_pat')
    def keyword_exp_and_pat(self, p):
        return Keyword(p, arg=p[0], value=p[2])

    @_('map_unpack_exp_and_pat')
    def keyword_exp_and_pat(self, p):
        return p[0]

    @_('NAME ":" exp_not_pat',
       'END ":" exp_not_pat')
    def keyword_exp_not_pat(self, p):
        return Keyword(p, arg=p[0], value=p[2])

    @_('map_unpack_exp_not_pat')
    def keyword_exp_not_pat(self, p):
        return p[0]

    @_('NAME ":" pat_not_exp',
       'END ":" pat_not_exp')
    def keyword_pat_not_exp(self, p):
        return Keyword(p, arg=p[0], value=p[2])

    @_('NAME ":" exp_and_pat "=" exp',
       'END ":" exp_and_pat "=" exp',
       'NAME ":" pat_not_exp "=" exp',
       'END ":" pat_not_exp "=" exp')
    def keyword_pat_not_exp(self, p):
        return Keyword(p, arg=p[0], value=p[2], default=p[4])

    @_('NAME "=" exp')
    def keyword_pat_not_exp(self, p):
        return Keyword(p, arg=p[0], value=Name(p, s=p[0]), default=p[2])

    @_('map_unpack_pat_not_exp')
    def keyword_pat_not_exp(self, p):
        return p[0]

    @_('name_keywords_exp_and_pat "," name_keyword_exp_and_pat')
    def name_keywords_exp_and_pat(self, p):
        return p[0] + [p[2]]

    @_('name_keyword_exp_and_pat')
    def name_keywords_exp_and_pat(self, p):
        return [p[0]]

    @_('name_keywords_exp_and_pat "," name_keyword_exp_not_pat',
       'name_keywords_exp_not_pat "," name_keyword_exp_and_pat',
       'name_keywords_exp_not_pat "," name_keyword_exp_not_pat')
    def name_keywords_exp_not_pat(self, p):
        return p[0] + [p[2]]

    @_('name_keyword_exp_not_pat')
    def name_keywords_exp_not_pat(self, p):
        return [p[0]]

    @_('name_keywords_exp_and_pat "," name_keyword_pat_not_exp',
       'name_keywords_pat_not_exp "," name_keyword_exp_and_pat',
       'name_keywords_pat_not_exp "," name_keyword_pat_not_exp')
    def name_keywords_pat_not_exp(self, p):
        return p[0] + [p[2]]

    @_('name_keyword_pat_not_exp')
    def name_keywords_pat_not_exp(self, p):
        return [p[0]]

    @_('NAME')
    def name_keyword_exp_and_pat(self, p):
        return Keyword(p, arg=p[0], value=Name(p, s=p[0]))

    @_('keyword_exp_and_pat')
    def name_keyword_exp_and_pat(self, p):
        return p[0]

    @_('keyword_exp_not_pat')
    def name_keyword_exp_not_pat(self, p):
        return p[0]

    @_('keyword_pat_not_exp')
    def name_keyword_pat_not_exp(self, p):
        return p[0]

    @_('LET pat "=" exp')
    def match(self, p):
        return Match(p, pattern=p[1], value=p[3])

    @_('DEF name arguments ":" block END')
    def function(self, p):
        return Function(p, name=p[1], args=p[2], body=p[4])

    @_('"(" arguments_pat ")"')
    def arguments(self, p):
        return Arguments(p, args=p[1][0], vararg=p[1][1], kwonlyargs=p[1][2], kwarg=p[1][3])

    @_('name_keyword_pat "," arguments_pat')
    def arguments_pat(self, p):
        return ([p[0]] + p[2][0],) + p[2][1:]

    @_('name_keyword_pat')
    def arguments_pat(self, p):
        return ([p[0]], None, [], None)

    @_('arguments_pat_args')
    def arguments_pat(self, p):
        return p[0]

    @_('default_pat "," arguments_pat_args')
    def arguments_pat_args(self, p):
        return ([p[0]] + p[2][0],) + p[2][1:]

    @_('default_pat')
    def arguments_pat_args(self, p):
        return ([p[0]], None, [], None)

    @_('arguments_pat_vararg')
    def arguments_pat_args(self, p):
        return ([],) + p[0]

    @_('tuple_unpack_pat "," arguments_pat_kwonly')
    def arguments_pat_vararg(self, p):
        return (p[0],) + p[2]

    @_('tuple_unpack_pat')
    def arguments_pat_vararg(self, p):
        return (p[0], [], None)

    @_('arguments_pat_kwarg')
    def arguments_pat_vararg(self, p):
        return (None, [], p[0])

    @_('argument_pat "," arguments_pat_kwonly')
    def arguments_pat_kwonly(self, p):
        return ([p[0]] + p[2][0], p[2][1])

    @_('argument_pat')
    def arguments_pat_kwonly(self, p):
        return ([p[0]], None)

    @_('arguments_pat_kwarg')
    def arguments_pat_kwonly(self, p):
        return ([], p[0])

    @_('map_unpack_pat')
    def arguments_pat_kwarg(self, p):
        return p[0]

    @_('')
    def arguments_pat_kwarg(self, p):
        return None

    @_('default_pat',
       'name_keyword_pat')
    def argument_pat(self, p):
        return p[0]

    @_('name_keyword_pat "=" exp')
    def default_pat(self, p):
        return Keyword(p, arg=p[0].arg, value=p[0].value, default=p[2])

    @_('NAME')
    def name_keyword_pat(self, p):
        return Keyword(p, arg=p[0], value=Name(p, s=p[0]))

    @_('keyword_pat')
    def name_keyword_pat(self, p):
        return p[0]

    @_('NAME ":" pat',
       'END ":" pat')
    def keyword_pat(self, p):
        return Keyword(p, arg=p[0], value=p[2])

    @_('tuple_unpack_exp_and_pat',
       'tuple_unpack_pat_not_exp')
    def tuple_unpack_pat(self, p):
        return p[0]

    @_('map_unpack_exp_and_pat',
       'map_unpack_pat_not_exp')
    def map_unpack_pat(self, p):
        return p[0]

    @_('')
    def empty(self, p):
        return []
