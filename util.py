import re

from typing import Callable, TypeVar

_T = TypeVar("_T")


VALIDATOR: dict[type[_T], Callable[[str], bool]] = {
    str: lambda x: True,
    int: lambda x: x.isdigit(),
    float: lambda x: re.match(r"^\d+\.\d+$", x) is not None,
    bool: lambda x: x in {"True", "False", "true", "false"},
}

CASTER: dict[type[_T], Callable[[str], _T]] = {
    str: lambda x: x,
    int: lambda x: int(x),
    float: lambda x: float(x),
    bool: lambda x: x.lower() == "true",
}


def type_cast(value: str, typ: type[_T]) -> _T:
    """
    简易类型转换

    Args:
        value: 待转换的值
        typ: 目标类型

    Returns:
        转换后的值

    Raises:
        NotImplementedError: 不支持的类型
        ValueError: 值不合法
    """
    if isinstance(value, typ):
        return value
    if typ not in VALIDATOR:
        raise NotImplementedError(f"Type {typ} is not supported")
    if not VALIDATOR[typ](value):
        raise ValueError(f"Invalid value for {typ}: {value}")
    return CASTER[typ](value)
