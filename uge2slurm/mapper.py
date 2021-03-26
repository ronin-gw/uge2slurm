import logging
from functools import wraps


class CommandMapperBase(object):
    _logger = logging.getLogger(__name__)

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
            if not callable(converter):
                continue

            mapmethod(dest)(converter)

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
        self._logger.warning('Converting option "{}" is not implemented.'. format(option_name))
    return _inner


def not_supported(option_name):
    def _inner(self, value):
        self._logger.warning('Converting option "{}" is not supported.'. format(option_name))
    return _inner


def mapmethod(*target_args):
    def _maker(func):
        @wraps(func)
        def _inner(self, *args, **kwargs):
            values = [getattr(self._args, arg) for arg in target_args]

            if len(values) == 1 and values[0] is None:
                return

            if args is not None:
                values += args

            additional_args = func(self, *values, **kwargs)

            input_repr = ", ".join("-{} {}".format(k, v) for k, v in zip(target_args, values))
            self._logger.debug(input_repr + " -> {}".format(additional_args))

            if additional_args:
                if isinstance(additional_args, (tuple, list)):
                    self.args += additional_args
                else:
                    self.args.append(additional_args)
        return _inner
    return _maker


try:  # py2 conpativility
    from functools import partialmethod  # novermin
except ImportError:
    from functools import partial

    class partialmethod(object):
        def __init__(self, func, *args, **keywords):
            if not callable(func) and not hasattr(func, "__get__"):
                raise TypeError("{!r} is not callable or a descriptor".format(func))

            if isinstance(func, partialmethod):
                self.func = func.func
                self.args = func.args + args
                self.keywords = {}
                self.keywords.update(**keywords)
            else:
                self.func = func
                self.args = args
                self.keywords = keywords

        def __repr__(self):
            args = ", ".join(map(repr, self.args))
            keywords = ", ".join("{}={!r}".format(k, v) for k, v in self.keywords.items())
            format_string = "{module}.{cls}({func}, {args}, {keywords})"
            return format_string.format(module=self.__class__.__module__,
                                        cls=self.__class__.__qualname__,
                                        func=self.func,
                                        args=args,
                                        keywords=keywords)

        def _make_unbound_method(self):
            def _method(cls_or_self, *args, **keywords):
                keywords.update(**self.keywords)
                return self.func(cls_or_self, *(self.args + args), **keywords)
            _method.__isabstractmethod__ = self.__isabstractmethod__
            _method._partialmethod = self
            return _method

        def __get__(self, obj, cls=None):
            get = getattr(self.func, "__get__", None)
            result = None
            if get is not None:
                new_func = get(obj, cls)
                if new_func is not self.func:
                    result = partial(new_func, *self.args, **self.keywords)
                    try:
                        result.__self__ = new_func.__self__
                    except AttributeError:
                        pass
            if result is None:
                result = self._make_unbound_method().__get__(obj, cls)
            return result

        @property
        def __isabstractmethod__(self):
            return getattr(self.func, "__isabstractmethod__", False)
