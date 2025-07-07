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

from collections.abc import Callable
from inspect import Parameter
from typing import Any


class DiError(Exception): ...


class DependencyNotFoundError(DiError):
    def __init__(self, dep_type: Any) -> None:
        super().__init__(f"Dependency not found for {dep_type}")


class NoUniqueDependencyError(DiError):
    def __init__(self, dep_type: Any) -> None:
        super().__init__(f"No unique dependency for type {dep_type}")


class UnrecognizableDependencyTypeError(DiError):
    def __init__(self, dep_type: Any) -> None:
        super().__init__(f"Unrecognizable dependency type {dep_type}")


class UnsupportedContainerTypeError(DiError):
    def __init__(self, dep_type: Any) -> None:
        super().__init__(f"Unsupported container type {dep_type}")


class UnsupportedGenericTypeError(DiError):
    def __init__(self, dep_type: Any) -> None:
        super().__init__(f"Unsupported generic type {dep_type}")


class ParameterNotAnnotatedError(DiError):
    def __init__(self, func: Callable[..., Any], param: Parameter) -> None:
        super().__init__(f"Parameter `{param.name}` of function `{func}` is not annotated")


class VarKeywordParameterNotSupportedError(DiError):
    def __init__(self, func: Callable[..., Any], param: Parameter) -> None:
        super().__init__(
            f"VAR_KEYWORD parameter `{param.name}` of function `{func}` is not supported"
        )


class VarPositionalParameterNotSupportedError(DiError):
    def __init__(self, func: Callable[..., Any], param: Parameter) -> None:
        super().__init__(
            f"VAR_POSITIONAL parameter `{param.name}` of function `{func}` is not supported"
        )


class ReturnTypeNotAnnotatedError(DiError):
    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__(f"Return of function `{func}` is not annotated")


class ReturnTypeIsNoneError(DiError):
    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__(f"Return of function `{func}` cannot be None or types.NoneType")


class ReturnTypeIsUnionError(DiError):
    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__(f"Return of function `{func}` cannot be types.UnionType")


class ReturnTypeIsNonTypeError(DiError):
    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__(f"Return of function `{func}` must be type")


class ConstructorExistsError(DiError):
    def __init__(self, func: Callable[..., Any]) -> None:
        super().__init__(f"Constructor `{func}` has already registered")
