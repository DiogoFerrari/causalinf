from .gcm_styles import resolve_graph_style, GRAPH_STYLES, GraphStyleInput
# 
from dataclasses import dataclass, replace, field
from typing import Literal, Optional, Dict
import contextvars
from contextlib import contextmanager

@dataclass(frozen=True)
class Options:
    print_fit_stats: bool = False
    print_assumptions: bool = False
    print_assumptions_verbose: bool = False
    # graph_style : dict = field(default_factory=lambda: STYLE_DEFAULT)
    graph_style: GraphStyleInput = "default"
    show_plot: bool = True

    # allow dict-like lookup
    def __getitem__(self, key: str):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __post_init__(self):
        # Because the dataclass is frozen, we must use object.__setattr__
        resolved = resolve_graph_style(self.graph_style, GRAPH_STYLES)
        object.__setattr__(self, "graph_style", resolved)

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
