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

from typing import Annotated

import managed._runtime_typing as rtt


def test_get_bases_of_primitive_types():
    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(int)) == (int, object)
    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(str)) == (str, object)


def test_get_bases_of_generic_types():
    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(list[int])) == (
        list[int],
        list,
        object,
    )
    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(dict[str, int])) == (
        dict[str, int],
        dict,
        object,
    )


def test_get_bases_of_annotated_types():
    class MySimpleBase:
        pass

    class MyObject(Annotated[MySimpleBase, 1]): ...  # pyright: ignore[reportGeneralTypeIssues, reportUntypedBaseClass]

    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(MyObject)) == (
        MyObject,
        Annotated[MySimpleBase, 1],
        MySimpleBase,
        object,
    )


def test_get_bases_of_user_defined_types():
    class MySimpleBase:
        pass

    class MyGenericBase[T](list[T]):
        pass

    class MyOtherGenericBase[T]:
        pass

    class MyGenericDerived[V](MyGenericBase[V], MyOtherGenericBase[int], MySimpleBase):
        pass

    assert rtt.get_bases(rtt.literal_typing_to_runtime_typing(MyGenericDerived[int])) == (
        MyGenericDerived[int],
        MyGenericDerived,
        MyGenericBase,
        list,
        MySimpleBase,
        rtt.TypingGeneric,
        object,
    )
