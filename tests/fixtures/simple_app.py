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
from typing import override

from managed import managed


@managed(as_="factory")
@dataclass
class SimpleDatabase: ...


@managed
@dataclass
class SimpleUserRepo:
    db: SimpleDatabase


@managed
@dataclass
class SimpleOrgRepo:
    db: SimpleDatabase


@managed
@dataclass
class SimpleUserService:
    repo: SimpleUserRepo


@managed
@dataclass
class SimpleOrgService:
    repo: SimpleOrgRepo


class Controller: ...


@managed
@dataclass
class SimpleUserController(Controller):
    svc: SimpleUserService

    @override
    def __hash__(self) -> int:  # only for test
        return id(self)


@managed
@dataclass
class SimpleOrgController(Controller):
    svc: SimpleOrgService

    @override
    def __hash__(self) -> int:  # only for test
        return id(self)


@managed
@dataclass
class SimpleApp:
    controllers: list[Controller]
