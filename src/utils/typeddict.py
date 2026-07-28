from typing import Any, get_origin


def validate_dict(data: Any, typeddict: type[Any], path: str = ""):
    if not isinstance(data, dict):
        raise TypeError(f"{path or "'data'"} must be a dictionary")

    if not hasattr(typeddict, "__annotations__"):
        raise TypeError("'typeddict' must be a TypedDict")

    for k, t in typeddict.__annotations__.items():
        path_k = f"{(path + '.') if path else ''}{k}"

        if k not in data:
            raise KeyError(f'Missing key "{path_k}"')

        origin_t = get_origin(t) or t
        val = data[k]  # pyright: ignore[reportUnknownVariableType]

        if hasattr(t, "__annotations__"):
            validate_dict(val, t, f"{(path + '.') if path else ''}{k}")
        elif not isinstance(val, origin_t):
            type_name = getattr(t, "__name__", str(t))
            raise TypeError(f'Value at "{path_k}" must be a {type_name}')
