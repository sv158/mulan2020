import sys
del sys.argv[0]
from types import ModuleType
from .compile import compile

mod = ModuleType("__main__")
sys.modules['__main__'] = mod.__dict__
filename = sys.argv[0] 

with open(filename, "r") as f:
    code = compile(f.read(), filename)

exec(code, mod.__dict__)
