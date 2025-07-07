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

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any, ClassVar, Final, NoReturn, cast, overload

from managed._providers import ConstructableProviderType


@overload
def managed[T](
    ctor: type[T],
    *,
    as_: ConstructableProviderType = ...,
) -> type[T]: ...


@overload
def managed[**P](
    ctor: Callable[P, Collection[Any]],
    *,
    as_: ConstructableProviderType = ...,
) -> NoReturn:
    """禁止将常见的容器 (list / tuple / set / dict) 作为依赖."""
    # 此 overload 需要早于下一个 managed() 声明,
    # 因为 overload 匹配选择是按声明顺序找到第1个匹配项


@overload
def managed[**P, R](
    ctor: Callable[P, R],
    *,
    as_: ConstructableProviderType = ...,
) -> Callable[P, R]: ...


@overload
def managed(
    ctor: None = None,
    *,
    as_: ConstructableProviderType = ...,
) -> ManagedWrapper: ...


def managed[T, **P, R](
    ctor: type[T] | Callable[P, R] | None = None,
    *,
    as_: ConstructableProviderType = "singleton",
) -> type[T] | Callable[P, R] | ManagedWrapper:
    if isinstance(ctor, type):  # 因为 type[T] 也是 callable, 所以先判断是否为 type
        return ManagedWrapper(provider_type=as_)(cast(type[T], ctor))

    elif callable(ctor):
        return ManagedWrapper(provider_type=as_)(ctor)

    else:
        return ManagedWrapper(provider_type=as_)


@dataclass(kw_only=True, repr=True)
class DependencyOption:
    provider_type: ConstructableProviderType


@dataclass(kw_only=True)
class ManagedWrapper:
    """Provide precise __call__() overload definition."""

    _DEPENDENCY_OPTION_KEY: ClassVar[Final[str]] = "__dependency_option__"

    provider_type: Final[ConstructableProviderType]

    @overload
    def __call__[T](self, ctor: type[T]) -> type[T]: ...

    @overload
    def __call__[**P, R](
        self,
        ctor: Callable[P, R],
    ) -> Callable[P, R]: ...

    def __call__[T, **P, R](
        self,
        ctor: type[T] | Callable[P, R],
    ) -> type[T] | Callable[P, R]:
        dependency_option = DependencyOption(provider_type=self.provider_type)
        setattr(ctor, self._DEPENDENCY_OPTION_KEY, dependency_option)
        return ctor

    @classmethod
    def get_dependency_option(
        cls,
        ctor: Callable[..., Any],
    ) -> DependencyOption | None:
        return getattr(ctor, cls._DEPENDENCY_OPTION_KEY, None)
