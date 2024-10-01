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
            if env_var.upper() in ["1", "ON", "TRUE", "ENABLED"]:
                return func(self, *args, **kwargs)
            else:
                logging.info(f"function '{func.__name__}' has been called, but has not been executed as '{env_var_name}' is not set.")
                return self
        return wrapper
    return decorator

