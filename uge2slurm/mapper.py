class CommandMapperBase:
    def __init__(self, bin):
        self.bin = bin
        self.args = []
        self.dest2converter = {}

    def convert(self, namespace):
        self._args = namespace

        self.pre_convert()

        namespace = vars(self._args)
        for dest, value in namespace.items():
            if value is None:
                continue
            converter = self.dest2converter.get(dest, getattr(self, dest, None))
            if callable(converter):
                converter(value)

        self.post_convert()

        return [self.bin] + self.args

    def pre_convert(self):
        pass

    def post_convert(self):
        pass


def bind_to(option):
    def _inner(self, value):
        self.args += [option, value]
    return _inner


def bind_if_true(option):
    def _inner(self, value):
        if value is True:
            self.args.append(option)
    return _inner


def not_implemented(option_name):
    def _inner(self, value):
        self._logger.warning('Converting option "{}" is not implemented'. format(option_name))
    return _inner


def not_supported(option_name):
    def _inner(self, value):
        self._logger.warning('Converting option "{}" is not supported'. format(option_name))
    return _inner
