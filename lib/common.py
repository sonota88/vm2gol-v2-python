class Token:
    def __init__(self, type, value, lineno):
        self.type = type
        self.value = value
        self.lineno = lineno

    def __str__(self):
        return self.__repr()

    def __repr__(self):
        return "(" + self.type + ": " + str(self.value) + ")"

    def get_value(self):
        if self.type == "ident":
            return self.value
        elif self.type == "int":
            return int(self.value)
        else:
            raise Exception("invalid type")
