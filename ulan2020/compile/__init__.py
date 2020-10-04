from .parse import Lexer, Parser
from .ast import TreeVisitor
from .scope import ScopeVisitor
from .symbol import SymbolTable
from .codegen import CodegenVisitor

def compile(text, filename, globals=()):
    try:
        lexer = Lexer(filename)
        parser = Parser(filename, text)
        tree = TreeVisitor(filename, text)
        scope = ScopeVisitor(filename, text)
        codegen = CodegenVisitor(filename, text)
        node = parser.parse(lexer.tokenize(text))
        node = tree.visit(node)
        symtable = SymbolTable()
        for name in globals:
            symtable[name] = symtable.get_global(name)
        scope.visit(node, symtable)
        return codegen.visit(node)
    except SyntaxError as e:
        raise e.with_traceback(None)

