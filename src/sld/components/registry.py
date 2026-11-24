"""Plugin-Registry für Komponenten."""

from typing import Callable, Literal, TypeVar

from pydantic import Field, create_model

from sld.components.base import Component

C = TypeVar("C", bound=type[Component])

_REGISTRY: dict[str, type[Component]] = {}
_version = 0


def register(name: str) -> Callable[[C], C]:
    """Klassen-Dekorator: meldet eine Komponente unter ``name`` an.

    Das Diskriminatorfeld ``type: Literal[name]`` wird automatisch ergänzt.
    """

    def deco(cls: C) -> C:
        global _version
        if name in _REGISTRY:
            raise ValueError(f"Komponente '{name}' ist bereits registriert ({_REGISTRY[name].__qualname__})")
        if not issubclass(cls, Component):
            raise TypeError(f"{cls.__name__} muss von sld.components.Component erben")
        model = create_model(
            cls.__name__,
            __base__=cls,
            __module__=cls.__module__,
            __doc__=cls.__doc__,
            type=(Literal[name], Field(name, description=f"Komponententyp ({cls.title or name})")),
        )
        model.type_name = name
        _REGISTRY[name] = model
        _version += 1
        return model  # type: ignore[return-value]

    return deco


def unregister(name: str) -> None:
    """Entfernt eine Komponente (v. a. für Tests)."""
    global _version
    _REGISTRY.pop(name, None)
    _version += 1


def get_component(name: str) -> type[Component]:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unbekannter Komponententyp '{name}'. Verfügbar: {', '.join(sorted(_REGISTRY))}") from None


def components() -> dict[str, type[Component]]:
    return dict(sorted(_REGISTRY.items()))


def registry_version() -> int:
    return _version
