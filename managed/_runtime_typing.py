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

import types
import typing
from collections import OrderedDict

from managed._utils import first

# ***************************************************
# ******* literal & runtime Type Hierarchy *******
# ***************************************************
# *
# ** type
# ** | >> instance: object, int
# ** |
# ** | >> instance: typing._GenericAlias
# ** |              | >>> instance: typing.List[int], UserDefined_GenericType[int]
# ** |              |
# ** |              |- typing._AnnotatedAlias
# ** |                 | >>> instance: Annotated[int, 1], Annotated[list[int], 1]
# ** |
# ** | >> instance: types.GenericAlias
# ** |              | >>> instance: list[int]
# ** |
# ** | >> instance: types.UnionType
# **                | >>> instance: int | str


# ! type checker cannot correctly convert literal typing to runtime typing,
# ! so we make these typing-check-only classes here for distinction when lint ourself.

if typing.TYPE_CHECKING:

    class Type(type):
        """type."""

    class Object(metaclass=Type):
        """object."""

else:
    Type = type
    Object = object


if typing.TYPE_CHECKING:

    class TypingGenericAlias(metaclass=Type):
        """typing._GenericAlias."""

    class TypingAnnotatedAlias(TypingGenericAlias):
        """typing._AnnotatedAlias."""

    class TypingGeneric[*Ts](metaclass=Type):
        """typing.Generic."""

else:
    TypingGenericAlias = type(typing.Iterable[int])
    TypingAnnotatedAlias = type(typing.Annotated[int, 1])
    TypingGeneric = typing.Generic

TypingTypeVar = typing.TypeVar
TypingTypeVarTuple = typing.TypeVarTuple


if typing.TYPE_CHECKING:

    class TypesGenericAlias(metaclass=Type):
        """types.GenericAlias."""

    class TypesUnionType(metaclass=Type):
        """types.UnionType."""

else:
    TypesGenericAlias = types.GenericAlias
    TypesUnionType = types.UnionType


GenericAlias = TypingGenericAlias | TypingAnnotatedAlias | TypesGenericAlias
MonadMetaType = GenericAlias | Type
MetaType = MonadMetaType | TypesUnionType


@typing.overload
def my_get_origin(t: GenericAlias, /) -> Type: ...


@typing.overload
def my_get_origin(t: TypesUnionType, /) -> type[TypesUnionType]: ...


@typing.overload
def my_get_origin(t: Type, /) -> None: ...


def my_get_origin(t: MetaType, /) -> typing.Any:
    return typing.get_origin(t)


@typing.overload
def my_get_args(
    t: TypesUnionType,
    /,
) -> tuple[MonadMetaType, ...]: ...


@typing.overload
def my_get_args(
    t: TypingAnnotatedAlias,
    /,
) -> tuple[TypingGenericAlias | TypesGenericAlias | Type | TypesUnionType]: ...


@typing.overload
def my_get_args(
    t: GenericAlias,
    /,
) -> tuple[MetaType, ...]: ...


def my_get_args(
    t: MetaType,
    /,
) -> tuple[MetaType, ...]:
    return typing.get_args(t)


@typing.overload
def literal_typing_to_runtime_typing(t: types.UnionType, /) -> TypesUnionType: ...


@typing.overload
def literal_typing_to_runtime_typing(t: type, /) -> MonadMetaType: ...


def literal_typing_to_runtime_typing(t: type | types.UnionType) -> MetaType:
    return typing.cast(typing.Any, t)


def unpack_if_union(t: MetaType) -> tuple[MonadMetaType, ...]:
    match t:
        case TypesUnionType():
            return my_get_args(t)
        case _:
            return (t,)


def _my_get_original_bases(t: Type) -> tuple[MonadMetaType, ...]:
    return types.get_original_bases(typing.cast(typing.Any, t))


def get_bases(t: MonadMetaType) -> tuple[MonadMetaType, ...]:
    result: OrderedDict[MonadMetaType, typing.Literal[True]] = OrderedDict()

    stack = [t]
    while stack:
        curr = stack.pop()

        match curr:
            case TypingAnnotatedAlias():
                result[curr] = True

                parent = first(my_get_args(curr))
                if isinstance(parent, TypesUnionType):
                    raise _ImpossibleError("cannot create 'types.UnionType' instances")

                stack.append(parent)

            case TypingGenericAlias() | TypesGenericAlias():
                orig = my_get_origin(curr)
                if orig is TypingGeneric:
                    continue

                result[curr] = True

                stack.append(orig)

            case Type():
                result[curr] = True

                stack.extend(reversed(_my_get_original_bases(curr)))  # deep-first

    if TypingGeneric in result:
        _ = result.pop(TypingGeneric, True)
        result[TypingGeneric] = True

    _ = result.pop(Object, True)
    result[Object] = True

    return tuple(result)

class T[*A, B]:
    t: tuple[*A]
    v: B

class A[**P, Z]: ...

T[int, str, float]().v

class Specialization(dict[])


class _ImpossibleError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
