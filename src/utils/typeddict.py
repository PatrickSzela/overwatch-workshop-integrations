from typing import Any


def validate_typeddict(data: Any, typeddict: type[Any], path: str = ""):
    if not isinstance(data, dict):
        raise TypeError(f"{path or "'data'"} must be a dictionary")

    if not hasattr(typeddict, "__annotations__"):
        raise TypeError("'typeddict' must be a TypedDict")

    for k, t in typeddict.__annotations__.items():
        if k not in data:
            raise KeyError(f"Missing {(path + '.') if path else ''}{k}")

        val = data[k]  # pyright: ignore[reportUnknownVariableType]

        if hasattr(t, "__annotations__"):  # nested TypedDict
            validate_typeddict(val, t, f"{(path + '.') if path else ''}{k}")
        elif not isinstance(val, t):
            raise TypeError(
                f"{(path + '.') if path else ''}{k} must be a {t.__name__}"
            )
