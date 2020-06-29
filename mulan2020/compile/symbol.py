class Symbol:
    pass


class SymbolTable:

    def __init__(self, parent=None):
        self.parent = parent
        self.names = []

    def get_name_slot(self, name):
        try:
            return self.names.index(name)
        except ValueError:
            slot = len(self.names)
            self.names.append(name)
            return slot

    def __getitem__(self, name):
        pass

    def get_slots(self):
        varnames = []
        freenames = []
        cellnames = []
        freevars = []        
        return tuple(self.names), tuple(varnames), tuple(freenames), tuple(cellnames), tuple(freevars)
