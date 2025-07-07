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

from typing import Any

from managed import DependencyRegistry
from tests.fixtures import collection_dep, ctor_dep, dataclass_dep, generic_dep, simple_app


def test_registry_register_val():
    class MyObject: ...

    obj = MyObject()

    reg = DependencyRegistry().register_val(obj)

    # twice
    assert reg.get_dependency(MyObject) is obj
    assert reg.get_dependency(MyObject) is obj


def test_collection_dep():
    reg = DependencyRegistry().scan([collection_dep])

    deps = reg.get_dependencies(collection_dep.Base)
    assert len(deps) == 3
    assert {
        type(deps[0]),
        type(deps[1]),
        type(deps[2]),
    } == {
        collection_dep.Child1,
        collection_dep.Child2,
        collection_dep.Child3,
    }


def test_ctor_dep():
    reg = DependencyRegistry().scan([ctor_dep])

    dep = reg.get_dependency(ctor_dep.Service)
    assert isinstance(dep.repo, ctor_dep.Repo)


def test_dataclass_dep():
    reg = DependencyRegistry().scan([dataclass_dep])

    dep = reg.get_dependency(dataclass_dep.Service)
    assert isinstance(dep.repo, dataclass_dep.Repo)


def test_generic_dep():
    reg = DependencyRegistry().scan([generic_dep])

    deps = reg.get_dependencies(generic_dep.Service[generic_dep.PgRepo])
    assert len(deps) == 1
    assert isinstance(deps[0], generic_dep.PgUserService)
    assert isinstance(deps[0].repo, generic_dep.PgRepo)


def test_simple_app():
    reg = DependencyRegistry().scan([simple_app])

    app = reg.get_dependency(simple_app.SimpleApp)

    assert isinstance(app, simple_app.SimpleApp)

    assert len(app.controllers) == 2
    assert app.controllers[0] is not app.controllers[1]
    assert type(app.controllers[0]) is not type(app.controllers[1])
    assert {
        type(app.controllers[0]),
        type(app.controllers[1]),
    } == {
        simple_app.SimpleUserController,
        simple_app.SimpleOrgController,
    }

    user_db: Any | None = None
    org_db: Any | None = None

    for controller in app.controllers:
        match controller:
            case simple_app.SimpleUserController():
                assert controller is reg.get_dependency(simple_app.SimpleUserController)

                assert controller.svc is reg.get_dependency(simple_app.SimpleUserService)

                assert controller.svc.repo is reg.get_dependency(simple_app.SimpleUserRepo)

                user_db = controller.svc.repo.db

            case simple_app.SimpleOrgController():
                assert controller is reg.get_dependency(simple_app.SimpleOrgController)

                assert controller.svc is reg.get_dependency(simple_app.SimpleOrgService)

                assert controller.svc.repo is reg.get_dependency(simple_app.SimpleOrgRepo)

                org_db = controller.svc.repo.db

            case _:
                raise Exception("never")

    assert user_db is not org_db
    assert type(user_db) is type(org_db)
    assert user_db is not reg.get_dependency(simple_app.SimpleDatabase)
    assert org_db is not reg.get_dependency(simple_app.SimpleDatabase)
