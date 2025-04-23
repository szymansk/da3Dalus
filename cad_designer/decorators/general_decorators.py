import os
import logging
from functools import wraps

def conditional_execute(env_var_name):
    """ Decorated function will be executed if env_var_name belongs to an environment variable.
    That is defined with one of "1", "ON", "TRUE" or "ENABLED".
    :param env_var_name: Environment variable name.
    :return: decorated function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            env_var = os.getenv(env_var_name)
            if env_var is not None and env_var.upper() in ["1", "ON", "TRUE", "ENABLED"]:
                return func(self, *args, **kwargs)
            else:
                logging.warning(f"function '{func.__name__}' has been called, but has not been executed as '{env_var_name}' is not set.")
                return self
        return wrapper
    return decorator

from inspect import signature
from typing import TypeVar, Type

T = TypeVar("T")

def fluent_init(cls: Type[T]) -> Type[T]:
    init_sig = signature(cls.__init__)
    params = list(init_sig.parameters.values())[1:]

    @staticmethod
    @wraps(cls.__init__)
    def init_method(*args, **kwargs) -> T:
        return cls(*args, **kwargs)

    init_method.__signature__ = init_sig.replace(parameters=params)  # type: ignore
    setattr(cls, "init", init_method)
    return cls