from .error import Error

class MatchDescriptor(dict):

    def __get__(self, instance, owner):
        def wrapper(node, *args, **kwargs):
            return self[type(node)](instance, node, *args, **kwargs)
        return wrapper

class VisitorMetaDict(dict):
    def __setitem__(self, name, value):
        if isinstance(value, MatchDescriptor):
            value.update(self.get(name, {}))
        super().__setitem__(name, value)

class VisitorMeta(type):

    @classmethod
    def __prepare__(self, name, bases):
        d = VisitorMetaDict()
        def _(*types):
            def decorator(func):
                return MatchDescriptor({t:func for t in types})
            return decorator
        d['_'] = _
        return d

    def __new__(self, name, bases, attrs):
        attrs.pop("_")
        return type.__new__(self, name, bases, attrs)

class Visitor(Error, metaclass=VisitorMeta):

    def __init__(self, filename, text):
        self.filename = filename
        self.text = text

