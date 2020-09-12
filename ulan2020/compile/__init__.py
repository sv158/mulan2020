from .parse import Lexer, Parser
from .ast import TreeVisitor
from .scope import ScopeVisitor
from .codegen import CodegenVisitor

def compile(text, filename):
    try:
        lexer = Lexer(filename)
        parser = Parser(filename, text)
        tree = TreeVisitor(filename, text)
        scope = ScopeVisitor(filename, text)
        codegen = CodegenVisitor(filename, text)
        node = parser.parse(lexer.tokenize(text))
        node = tree.visit(node)
        scope.visit(node)
        return codegen.visit(node)
    except SyntaxError as e:
        raise e.with_traceback(None)

