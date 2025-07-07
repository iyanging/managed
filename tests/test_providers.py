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

from managed._providers import (
    FactoryProvider,
    ListProvider,
    ObjectProvider,
    SingletonProvider,
)


def test_factory_provider_returns_new_instance_each_time():
    class Foo: ...

    provider = FactoryProvider(Foo)
    a = provider()
    b = provider()

    assert isinstance(a, Foo)
    assert isinstance(b, Foo)
    assert a is not b


def test_factory_provider():
    class Foo:
        pass

    @dataclass
    class Bar:
        foo: Foo

    provider = FactoryProvider(
        Bar,
        FactoryProvider(Foo),
    )

    a = provider()
    assert isinstance(a, Bar)
    assert isinstance(a.foo, Foo)

    b = provider()
    assert isinstance(b, Bar)
    assert isinstance(b.foo, Foo)

    assert a is not b
    assert a.foo is not b.foo


def test_singleton_provider():
    class Baz:
        pass

    provider = SingletonProvider(Baz)
    a = provider()
    b = provider()
    assert isinstance(a, Baz)
    assert a is b


def test_singleton_provider_with_args():
    class Foo:
        pass

    provider = SingletonProvider(Foo)

    a = provider()
    b = provider()
    assert a is b


def test_object_provider():
    obj = {"foo": "bar"}
    provider = ObjectProvider(obj)
    assert provider() is obj


def test_list_provider_returns_new_list_each_time():
    p1 = ObjectProvider(1)
    p2 = ObjectProvider(2)
    provider = ListProvider([p1, p2])
    l1 = provider()
    l2 = provider()
    assert l1 == [1, 2]
    assert l2 == [1, 2]
    assert l1 is not l2
