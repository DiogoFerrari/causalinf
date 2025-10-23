from dataclasses import dataclass, replace
from typing import Literal, Optional
import contextvars
from contextlib import contextmanager

@dataclass(frozen=True)
class Options:
    print_fit_stats: bool = False
    print_assumptions: bool = False
    print_assumptions_verbose: bool = False
    graph_style:str = 'default'
    show_plot: bool = True

    # allow dict-like lookup
    def __getitem__(self, key: str):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

_default_options = Options()
# _current: contextvars.ContextVar[Options] = contextvars.ContextVar("opts", default=_default_options)
_current = contextvars.ContextVar("opts", default=_default_options)


def get_options(key: Optional[str] = None):
    opts = _current.get()
    if key is None:
        return opts
    return opts[key]

def set_options(**overrides):
    _current.set(replace(_current.get(), **overrides))

def reset_options():
    _current.set(_default_options)

@contextmanager
def option_context(**overrides):
    token = None
    try:
        token = _current.set(replace(_current.get(), **overrides))
        yield
    finally:
        if token is not None:
            _current.reset(token)
