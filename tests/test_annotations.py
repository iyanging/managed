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

from dataclasses import dataclass

from managed import managed
from managed._annotations import ManagedWrapper


def test_managed_dataclass():
    @managed(as_="singleton")
    @dataclass
    class Service:
        a: int
        b: str

    _ = Service(a=1, b="test")

    dep_opt = ManagedWrapper.get_dependency_option(Service)
    assert dep_opt is not None
    assert dep_opt.provider_type == "singleton"


def test_managed_ctor():
    @managed(as_="factory")
    class Service:
        def __init__(self, a: int, b: str) -> None:
            self.a = a
            self.b = b

    _ = Service(1, "test")

    dep_opt = ManagedWrapper.get_dependency_option(Service)
    assert dep_opt is not None
    assert dep_opt.provider_type == "factory"
