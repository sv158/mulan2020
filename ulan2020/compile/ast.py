import typing
from .visit import Visitor
from . import parse


class Node:

    def __init__(self, *args, **kwargs):
        if args:
            p = args[0]
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

class Pattern(Node):
    pass

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

class Tuple(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class List(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class Set(Expression):
    elts: typing.List[typing.Union[Expression, Unpack]]

class UnpackPattern(Node):
    value: Pattern

class Arguments(Node):
    args: typing.List[Pattern]
    vararg: typing.Optional[UnpackPattern]
    kwonlyargs: typing.List[Pattern]
    kwarg: typing.Optional[UnpackPattern]

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

class Module(Expression):
    level: int
    path: typing.List[str]

class ModuleAttribute(Expression):
    value: Module
    identifier: str

class Attribute(Expression):
    value: Expression
    identifier: str

class Subscript(Expression):
    value: Expression
    slice: Expression

class Keyword(Expression):
    arg: str
    value: Expression

class Call(Expression):
    func: Expression
    args: typing.List[typing.Union[Expression, Unpack]]
    keywords: typing.List[typing.Union[Keyword, Unpack]]

class Literal(Expression):
    value: typing.Union[int, float, str]

class Match(Condition):
    pattern: Pattern
    value: Expression

class LiteralPattern(Pattern):
    value: typing.Union[int, float, str]

class NamePattern(Pattern):
    s: str

class KeywordPattern(Pattern):
    arg: str
    value: Pattern
    default: typing.Optional[Expression]

class TreeVisitor(Visitor):

    @_(parse.File)
    def visit(self, node):
        return File(node, body=[self.visit(e) for e in node.body])

    @_(parse.Submodule)
    def visit(self, node):
        name = node.name or "builtins"

        if node.parent is None:
            if name == "self":
                return Module(node, level=1, path=[])
            elif name == "super":
                return Module(node, level=2, path=[])
            else:
                return Module(node, level=0, path=[name])

        level = node.parent.level
        path = node.parent.path
        if name == "self":
            self.error(node, "self not allowed")
        elif name == "super":
            if (level < 2) or path:
                self.error(node, "super not allowed")
            return Module(node, level=level+1, path=path)
        return Module(node, level=level, path=path+[name])

    @_(parse.Attribute)
    def visit(self, node):
        value = self.visit(node.value)
        if isinstance(value, Module):
            return ModuleAttribute(node, value=value, identifier=node.identifier)
        return Attribute(node, value=value, identifier=node.identifier)

    @_(parse.Subscript)
    def visit(self, node):
        return Subscript(
            node,
            value=self.visit(node.value),
            slice=self.visit(node.slice))

    @_(parse.Tuple)
    def visit(self, node):
        return Tuple(node, elts=[self.visit(e) for e in node.elts])

    @_(parse.List)
    def visit(self, node):
        return List(node, elts=[self.visit(e) for e in node.elts])

    @_(parse.Set)
    def visit(self, node):
        return Set(node, elts=[self.visit(e) for e in node.elts])

    @_(parse.Call)
    def visit(self, node):
        return Call(
            node,
            func=self.visit(node.func),
            args=[self.visit(e) for e in node.args],
            keywords=[self.visit(e) for e in node.keywords])

    @_(parse.Keyword)
    def visit(self, node):
        return Keyword(
            node,
            arg=node.arg,
            value=self.visit(node.value))

    @_(parse.Literal)
    def visit(self, node):
        return Literal(node, value=node.value)

    @_(parse.Name)
    def visit(self, node):
        return Name(node, s=node.s)

    @_(parse.Arguments)
    def visit(self, node):
        return Arguments(
            node,
            args=[self.visit_pattern(s) for s in node.args],
            vararg=None if node.vararg is None else self.visit_pattern(node.vararg.value),
            kwonlyargs=[self.visit_pattern(s) for s in node.kwonlyargs],
            kwarg=None if node.kwarg is None else self.visit_pattern(node.kwarg.value))

    @_(parse.Function)
    def visit(self, node):
        return Function(
            node,
            name=self.visit(node.name),
            args=self.visit(node.args),
            body=[self.visit(s) for s in node.body])

    @_(parse.If)
    def visit(self, node):
        return If(
            node,
            test=self.visit(node.test),
            body=[self.visit(s) for s in node.body],
            orelse=[self.visit(s) for s in node.orelse])

    @_(parse.Return)
    def visit(self, node):
        return Return(
            node,
            value=self.visit(node.value))

    @_(parse.Match)
    def visit(self, node):
        return Match(
            node,
            pattern=self.visit_pattern(node.pattern),
            value=self.visit(node.value))

    @_(parse.Literal)
    def visit_pattern(self, node):
        return LiteralPattern(node, value=node.value)

    @_(parse.Name)
    def visit_pattern(self, node):
        return NamePattern(node, s=node.s)

    @_(parse.Keyword)
    def visit_pattern(self, node):
        return KeywordPattern(
            node,
            arg=node.arg,
            value=self.visit_pattern(node.value),
            default=None if getattr(node, 'default', None) is None else self.visit(node.default))
