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

import logging
import types
import typing
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable
from dataclasses import MISSING, dataclass, fields, is_dataclass
from importlib import import_module
from inspect import Parameter, getmembers, signature
from pkgutil import walk_packages

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance

import managed._runtime_typing as rtt
from managed._annotations import DependencyOption, ManagedWrapper
from managed._providers import (
    ConstructableProvider,
    ListProvider,
    ObjectProvider,
    Provider,
    provider_type_to_class,
)
from managed._utils import first, first_not_none
from managed.errors import (
    ConstructorExistsError,
    DependencyNotFoundError,
    DiError,
    NoUniqueDependencyError,
    ParameterNotAnnotatedError,
    ReturnTypeIsNoneError,
    ReturnTypeIsNonTypeError,
    ReturnTypeIsUnionError,
    ReturnTypeNotAnnotatedError,
    UnrecognizableDependencyTypeError,
    UnsupportedContainerTypeError,
    UnsupportedGenericTypeError,
    VarKeywordParameterNotSupportedError,
    VarPositionalParameterNotSupportedError,
)

type _DependencyCtor = Callable[..., typing.Any]


@dataclass
class _DependencyCtorContext:
    option: DependencyOption
    provider: Provider[typing.Any] | None


class DependencyRegistry:
    _logger: logging.Logger

    # The reason why not combine these status into one is that:
    #   * keep the semantic: "one ctor in diff proto has the same provider"
    #   * provider cannot be eagerly built, due to the possible absence of deps
    _proto_to_ctor_set: defaultdict[rtt.TypingGenericAlias | rtt.Type, set[_DependencyCtor]]
    _ctor_to_ctx: dict[_DependencyCtor, _DependencyCtorContext]

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._proto_to_ctor_set = defaultdict(set)
        self._ctor_to_ctx = {}

        _ = self.register_val(None)
        _ = self.register_val(self)

    def get_dependency[T](self, dep_type: type[T]) -> T:
        dep_rtt = rtt.literal_typing_to_runtime_typing(dep_type)

        provider = first_not_none(
            self._get_or_make_provider_from_registry(
                possible_dep_rtt,
                require_most_one_provider=True,
            )
            for possible_dep_rtt in rtt.unpack_if_union(dep_rtt)
        )

        if provider is None:
            raise DependencyNotFoundError(dep_rtt)

        self._logger.debug("Found %s", provider)

        dep = provider()

        self._logger.debug(
            "Return %s (id: %s)",
            type(dep),  # pyright: ignore[reportUnknownArgumentType]
            id(dep),
        )

        return dep

    def get_dependencies[T](self, dep_type: type[T]) -> list[T]:
        dep_rtt = rtt.literal_typing_to_runtime_typing(dep_type)

        providers = first_not_none(
            self._get_or_make_provider_from_registry(
                possible_dep_rtt,
                require_most_one_provider=False,
            )
            for possible_dep_rtt in rtt.unpack_if_union(dep_rtt)
        )

        if not providers:
            raise DependencyNotFoundError(dep_rtt)

        provider = ListProvider(providers)

        self._logger.debug("Built an temporarily %s", provider)

        dep = provider()

        self._logger.debug(
            "Return %s (id: %s)",
            type(first(dep)),  # pyright: ignore[reportUnknownArgumentType]
            id(dep),
        )

        return dep

    def scan(
        self,
        modules: Iterable[types.ModuleType],
    ) -> typing.Self:
        dep_def_list = self._gather_dep_def_from_modules(modules)

        for ctor, option in dep_def_list:
            self.register_ctor(ctor, option)

        return self

    @typing.overload
    def register_ctor(
        self,
        ctor: Callable[..., None],
        option: DependencyOption,
    ) -> typing.NoReturn: ...

    @typing.overload
    def register_ctor(
        self,
        ctor: Callable[..., typing.Any],
        option: DependencyOption,
    ) -> typing.Self: ...

    def register_ctor(
        self,
        ctor: Callable[..., typing.Any],
        option: DependencyOption,
    ) -> typing.Self:
        prototypes = self._get_prototypes_by_ctor(ctor)

        for proto in prototypes:
            if not isinstance(proto, rtt.TypingGenericAlias | rtt.Type):
                continue

            ctor_set = self._proto_to_ctor_set[proto]

            if ctor not in ctor_set:
                ctor_set.add(ctor)
                self._ctor_to_ctx[ctor] = _DependencyCtorContext(
                    option=option,
                    provider=None,
                )

            else:
                raise ConstructorExistsError(ctor)

        return self

    def register_val(self, v: object) -> typing.Self:
        ctor = _ObjectCtor(v)
        prototypes = rtt.get_bases(rtt.literal_typing_to_runtime_typing(type(v)))

        for proto in prototypes:
            if not isinstance(proto, rtt.TypingGenericAlias | rtt.Type):
                continue

            ctor_set = self._proto_to_ctor_set[proto]

            if ctor not in ctor_set:
                ctor_set.add(ctor)
                self._ctor_to_ctx[ctor] = _DependencyCtorContext(
                    option=DependencyOption(provider_type="singleton"),
                    provider=ObjectProvider(v),
                )

            else:
                raise ConstructorExistsError(ctor)

        return self

    @typing.overload
    def _get_or_make_provider_from_registry(
        self,
        dep_type: rtt.MetaType,
        *,
        require_most_one_provider: typing.Literal[True],
    ) -> Provider[typing.Any] | None: ...

    @typing.overload
    def _get_or_make_provider_from_registry(
        self,
        dep_type: rtt.MetaType,
        *,
        require_most_one_provider: typing.Literal[False],
    ) -> list[Provider[typing.Any]] | None: ...

    def _get_or_make_provider_from_registry(  # noqa: C901, PLR0911, PLR0912
        self,
        dep_type: rtt.MetaType,
        *,
        require_most_one_provider: bool,
    ) -> Provider[typing.Any] | list[Provider[typing.Any]] | None:
        # Eg:
        # `Annotated[list[Service], 1]`: Annotated + (list[Service], 1)
        # `Annotated[int, 1]`: Annotated + (int, 1)
        # `Annotated[Annotated[int, 1], 2]`: Annotated + (int, 1, 2)
        if isinstance(dep_type, rtt.TypingAnnotatedAlias):
            unannotated = first(rtt.my_get_args(dep_type))  # such as `list[Service]`, `int`
            return self._get_or_make_provider_from_registry(
                unannotated,
                require_most_one_provider=require_most_one_provider,
            )

        # Eg: `List[Service]`, `list[Service]`, `typing.Iterable[Service]`, `App[Service]`
        elif isinstance(dep_type, rtt.TypingGenericAlias | rtt.TypesGenericAlias):
            origin_type = rtt.my_get_origin(dep_type)

            # `List[Service]`: list + (Service,)  # same as `list[Service]`
            # `typing.Iterable[Service]`: collections.abc.Iterable + (Service,)
            # `collections.abc.Iterable[Service]`: collections.abc.Iterable + (Service,)
            if issubclass(origin_type, Collection):
                if issubclass(origin_type, Iterable):
                    real_dep_type = first(rtt.my_get_args(dep_type))  # such as `Service`
                    providers = self._get_or_make_provider_from_registry(
                        real_dep_type,
                        require_most_one_provider=False,
                    )

                    return ListProvider(providers) if providers is not None else None

                else:  # such as `dict[str, Service]`
                    raise UnsupportedContainerTypeError(dep_type)

            elif isinstance(dep_type, rtt.TypesGenericAlias):
                raise UnsupportedGenericTypeError(dep_type)

            # `App[Service]`
            else:
                pass

        # Eg: `Service | None`
        elif isinstance(dep_type, rtt.TypesUnionType):
            dep_type_args = typing.get_args(dep_type)  # such as `(Service, types.NoneType)`

            is_optional = False
            found_dep: Provider[typing.Any] | None = None

            # find first managed dependency
            for possible_dep_type in dep_type_args:
                if possible_dep_type is types.NoneType:
                    is_optional = True

                else:
                    try:
                        found_dep = self._get_or_make_provider_from_registry(
                            possible_dep_type,
                            require_most_one_provider=True,
                        )
                        break

                    except DiError:
                        pass

            if found_dep is None:
                if not is_optional:
                    raise DependencyNotFoundError(dep_type)

                else:
                    return ObjectProvider(None)

            else:
                return found_dep

        # Eg: `Service`
        elif isinstance(dep_type, rtt.Type):  # pyright: ignore[reportUnnecessaryIsInstance]
            pass

        else:
            raise UnrecognizableDependencyTypeError(dep_type)

        # Here we will get: `App[Service]`, `Service`

        providers = self._do_get_or_make_providers(dep_type)
        if providers is None:
            return None

        if require_most_one_provider:
            if len(providers) != 1:
                raise NoUniqueDependencyError(dep_type)
            else:
                return providers[0]

        else:
            return providers

    def _do_get_or_make_providers(
        self,
        dep_type: rtt.TypingGenericAlias | rtt.Type,
    ) -> list[Provider[typing.Any]] | None:
        dep_ctor_set = self._proto_to_ctor_set.get(dep_type, None)
        if dep_ctor_set is None:
            return None

        providers: list[Provider[typing.Any]] = []
        for ctor in dep_ctor_set:
            ctx = self._ctor_to_ctx.get(ctor, None)
            if ctx is None:
                continue

            if ctx.provider is None:
                ctx.provider = self._make_provider(ctor, ctx.option)

            providers.append(ctx.provider)

        return providers

    def _make_provider(
        self,
        ctor: Callable[..., typing.Any],
        option: DependencyOption,
    ) -> Provider[typing.Any]:
        provider_class = provider_type_to_class[option.provider_type]

        if is_dataclass(ctor):
            if isinstance(ctor, type):
                provider = self._make_provider_by_dataclass(ctor, provider_class)

            else:
                raise UnrecognizableDependencyTypeError(ctor)

        else:
            provider = self._make_provider_by_func(ctor, provider_class)

        return provider

    def _make_provider_by_dataclass(
        self,
        ctor: type[DataclassInstance],
        provider_class: type[ConstructableProvider[typing.Any]],
    ) -> Provider[typing.Any]:
        params = fields(ctor)
        annotations = typing.get_type_hints(ctor)
        kwargs: dict[str, Provider[typing.Any]] = {}

        for p in params:
            if not p.init:
                continue

            if p.default is not MISSING or p.default_factory is not MISSING:
                continue

            annotation = annotations[p.name]

            param_provider = self._get_or_make_provider_from_registry(
                annotation,
                require_most_one_provider=True,
            )
            if param_provider is None:
                raise DependencyNotFoundError(annotation)

            kwargs[p.name] = param_provider

        return provider_class(ctor, **kwargs)

    def _make_provider_by_func(
        self,
        ctor: Callable[..., typing.Any],
        provider_class: type[ConstructableProvider[typing.Any]],
    ) -> Provider[typing.Any]:
        params = list(signature(ctor, eval_str=True).parameters.values())

        args: list[typing.Any] = []
        kwargs: dict[str, Provider[typing.Any]] = {}

        for p in params:
            annotation = p.annotation

            if annotation is Parameter.empty:
                raise ParameterNotAnnotatedError(ctor, p)

            param_provider = self._get_or_make_provider_from_registry(
                annotation,
                require_most_one_provider=True,
            )
            if param_provider is None:
                raise DependencyNotFoundError(annotation)

            match p.kind:
                case Parameter.VAR_KEYWORD:
                    raise VarKeywordParameterNotSupportedError(ctor, p)

                case Parameter.VAR_POSITIONAL:
                    raise VarPositionalParameterNotSupportedError(ctor, p)

                case Parameter.POSITIONAL_ONLY:
                    args.append(param_provider)

                case Parameter.POSITIONAL_OR_KEYWORD:
                    args.append(param_provider)

                case Parameter.KEYWORD_ONLY:
                    kwargs[p.name] = param_provider

        return provider_class(ctor, *args, **kwargs)

    @staticmethod
    def _gather_dep_def_from_modules(
        modules: Iterable[types.ModuleType],
    ) -> list[tuple[type | Callable[..., typing.Any], DependencyOption]]:
        dep_def_list: list[
            tuple[
                type | Callable[..., typing.Any],
                DependencyOption,
            ]
        ] = []

        scanning_modules: set[types.ModuleType] = set()

        for module in modules:
            if not hasattr(module, "__path__"):  # single-file module, which do not have sub-module
                scanning_modules.add(module)

            else:
                for mod_info in walk_packages(module.__path__, f"{module.__name__}."):
                    mod = import_module(mod_info.name)
                    scanning_modules.add(mod)

        for mod in scanning_modules:
            for name, member in getmembers(mod):
                if name.startswith("_"):
                    continue

                option = ManagedWrapper.get_dependency_option(member)
                if option is None:
                    continue

                dep_def_list.append((member, option))

        return dep_def_list

    @staticmethod
    def _get_prototypes_by_ctor(
        ctor: Callable[..., typing.Any],
    ) -> tuple[rtt.MonadMetaType, ...]:
        if isinstance(ctor, type):
            ret_type = rtt.literal_typing_to_runtime_typing(ctor)

        else:
            ret_type = typing.get_type_hints(ctor).get("return", MISSING)

            if ret_type is MISSING:
                raise ReturnTypeNotAnnotatedError(ctor)

            if not isinstance(ret_type, type):
                raise ReturnTypeIsNonTypeError(ctor)

            if ret_type is types.NoneType:
                raise ReturnTypeIsNoneError(ctor)

            ret_type = rtt.literal_typing_to_runtime_typing(ret_type)

        if isinstance(ret_type, rtt.TypesUnionType):
            raise ReturnTypeIsUnionError(ctor)

        return rtt.get_bases(ret_type)


@dataclass(repr=True)
class _ObjectCtor:
    _val: typing.Any

    @typing.override
    def __hash__(self) -> int:
        return hash(self._val)

    def __call__(self) -> typing.Any:
        return self._val
