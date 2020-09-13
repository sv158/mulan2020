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


class Statement(Node):
    pass

class Condition(Statement):
    pass

class File(Node):
    body: typing.List[Statement]

class Expression(Condition):
    pass

class Unpack(Node):
    value: Expression

class If(Statement):
    test: Condition
    body: typing.List[Statement]
    orelse: typing.List[Statement]

class Module(Expression):
    level: int
    path: typing.List[str]

class ModuleAttribute(Expression):
    value: Module
    identifier: str

class Attribute(Expression):
    value: Expression
    identifier: str

class Keyword(Expression):
    arg: str
    value: Expression

class Call(Expression):
    func: Expression
    args: typing.List[typing.Union[Expression, Unpack]]
    keywords: typing.List[typing.Union[Keyword, Unpack]]

class Literal(Expression):
    value: typing.Union[int, float, str]


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

    @_(parse.If)
    def visit(self, node):
        return If(
            node,
            test=self.visit(node.test),
            body=[self.visit(s) for s in node.body],
            orelse=[self.visit(s) for s in node.orelse])
