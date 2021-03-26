from __future__ import absolute_import


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
