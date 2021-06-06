class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __str__(self):
        return self.__repr()

    def __repr__(self):
        return "(" + self.type + ": " + str(self.value) + ")"
