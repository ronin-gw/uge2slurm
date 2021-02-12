class CommandMapperBase:
    def __init__(self, bin):
        self.bin = bin
        self.args = []
        self.dest2converter = {}

    def convert(self, namespace):
        namespace = vars(namespace)

        self.pre_convert(namespace)

        for dest, value in namespace.items():
            if value is None:
                continue
            converter = self.dest2converter.get(dest, getattr(self, dest, None))
            if callable(converter):
                converter(value)

        self.post_convert(namespace)

        return [self.bin] + self.args

    def pre_convert(self, namespace):
        pass

    def post_convert(self, namespace):
        pass
