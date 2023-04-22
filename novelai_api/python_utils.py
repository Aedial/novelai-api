import inspect
import operator
from typing import Callable, Iterable, Union

NoneType: type = type(None)


def assert_type(expected, **types):
    for k, v in types.items():
        assert isinstance(v, expected), f"Expected type '{expected}' for {k}, but got type '{type(v)}'"


operator_to_str = {
    operator.eq: "exactly {} characters",
    operator.lt: "less than {} characters",
    operator.le: "{} characters or less",
    operator.gt: "more than {} characters",
    operator.ge: "{} characters or more",
}


def assert_len(expected, op: operator = operator.eq, **values):
    op_str = operator_to_str[op].format(expected)

    for k, v in values.items():
        assert v is None or op(len(v), expected), f"'{k}' should be {op_str}, got length of {len(v)}'"


def expand_kwargs(keys: Iterable[str], types: Union[Iterable[type], Iterable[type]]):
    types = [set(t) - {int} if isinstance(t, (tuple, list, set)) and int in t and float in t else t for t in types]
    types = [Union[tuple(t)] if isinstance(t, (tuple, list, set)) else t for t in types]

    kwargs_params = [inspect.Parameter(k, inspect.Parameter.KEYWORD_ONLY, annotation=v) for k, v in zip(keys, types)]

    def wrapper(func: Callable):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # find the **kwargs
        kwargs_pos = [i for i, param in enumerate(params) if param.kind is param.VAR_KEYWORD]
        if not kwargs_pos:
            raise ValueError(f"Couldn't find **kwargs for function {func}")
        pos = kwargs_pos[0]

        func.__signature__ = sig.replace(parameters=[*params[:pos], *kwargs_params, *params[pos + 1 :]])

        return func

    return wrapper
