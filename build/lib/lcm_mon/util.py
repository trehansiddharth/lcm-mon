import itertools

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

class Spinner:
    def __init__(self):
        self._spinner = itertools.cycle(['|', '/', '-', '\\'])

    def spin(self):
        return next(self._spinner)

def unpack_msg(msg):
    def valid_variable(name):
        specials = ["decode", "encode"]
        return not (name[:1] == "_" or name in specials)
    variables = [variable for variable in dir(msg) if valid_variable(variable)]
    return list(zip(variables, [getattr(msg, variable) for variable in variables]))
