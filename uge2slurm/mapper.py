import logging
from functools import wraps, partial


class CommandMapperBase(object):
    _logger = logging.getLogger(__name__)

    def __init__(self, bin):
        self.bin = bin
        self.args = []
        self.dest2converter = {}

    @classmethod
    def _get_unbound_method(cls, dest):
        return getattr(cls, dest, None)

    def convert(self, namespace):
        self._args = namespace

        self.pre_convert()

        namespace = vars(self._args)
        for dest, value in namespace.items():
            if value is None:
                continue

            converter = self.dest2converter.get(dest, self._get_unbound_method(dest))
            if not callable(converter) and not isinstance(converter, partial):
                continue

            mapmethod(dest)(converter)(self)

        self.post_convert()

        return [str(arg) for arg in [self.bin] + self.args]

    def pre_convert(self):
        pass

    def post_convert(self):
        pass


def bind_to(option):
    def _inner(self, value):
        return [option, value]
    return _inner


def bind_if_true(option):
    def _inner(self, value):
        if value is True:
            return [option]
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

        # python2.7 does not ignore AttributeError
        if not isinstance(func, partial):
            _inner = wraps(func)(_inner)

        return _inner
    return _maker
