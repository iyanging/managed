# Copyright 2025 iyanging
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Any, Literal, override


class Provider[T](ABC):
    """Abstraction of `call to provide`.

    Provider Hierarchy:

    ```
    Provider
    |
    |- ConstructableProvider
    |  |
    |  |- FactoryProvider
    |  |
    |  |- SingletonProvider
    |
    |- ObjectProvider
    |
    |- ListProvider
    ```

    Subclasses must handle initialization themselves.
    """

    @abstractmethod
    def __call__(self) -> T:
        raise NotImplementedError

    @override
    @abstractmethod
    def __repr__(self) -> str:
        raise NotImplementedError


class ConstructableProvider[T](Provider[T], ABC):
    """Abstraction of `must init then call to provide`."""

    @abstractmethod
    def __init__(
        self,
        ctor: Callable[..., T],
        *args: Provider[Any],
        **kwargs: Provider[Any],
    ) -> None:
        raise NotImplementedError


class FactoryProvider[T](ConstructableProvider[T]):
    _ctor: Callable[..., T]
    _args: tuple[Provider[Any], ...]
    _kwargs: Mapping[str, Provider[Any]]

    def __init__(
        self,
        ctor: Callable[..., T],
        *args: Provider[Any],
        **kwargs: Provider[Any],
    ) -> None:
        self._ctor = ctor
        self._args = args
        self._kwargs = kwargs

    @override
    def __call__(self) -> T:
        # use tuple() rather than generator to evaluate args before kwargs,
        # so we can simulate the normal function invocation
        args = tuple(arg() for arg in self._args)
        kwargs = {kw: arg() for kw, arg in self._kwargs.items()}

        return self._ctor(*args, **kwargs)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._ctor}, *, **)"


class SingletonProvider[T](ConstructableProvider[T]):
    _factory: FactoryProvider[T]
    _instance: T | None

    def __init__(
        self,
        ctor: Callable[..., T],
        *args: Provider[Any],
        **kwargs: Provider[Any],
    ) -> None:
        self._factory = FactoryProvider(ctor, *args, **kwargs)
        self._instance = None

    @override
    def __call__(self) -> T:
        if self._instance is not None:
            return self._instance

        else:
            self._instance = self._factory()

            return self._instance

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__qualname__}(_factory={self._factory}, _instance={self._instance})"
        )


class ObjectProvider[T](Provider[T]):
    _instance: T

    def __init__(self, obj: T) -> None:
        self._instance = obj

    @override
    def __call__(self) -> T:
        return self._instance

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}(_instance={self._instance})"


class ListProvider[T](Provider[list[T]]):
    _elements: list[Provider[T]]

    def __init__(self, elements: list[Provider[T]]) -> None:
        self._elements = [*elements]  # shallow copy

    @override
    def __call__(self) -> list[T]:
        # create a new list each time
        return [e() for e in self._elements]

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._elements})"


ConstructableProviderType = Literal["singleton", "factory"]

provider_type_to_class: dict[ConstructableProviderType, type[ConstructableProvider[Any]]] = {
    "singleton": SingletonProvider,
    "factory": FactoryProvider,
}
