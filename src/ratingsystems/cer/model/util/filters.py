from typing import Any, Callable

def contains(value) -> Callable[[Any], bool]:
    return lambda x: value in x
