# managed

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/license/apache-2-0)

「Simple yet Powerful」 dependency injection framework

## Roadmap

- [ ] support specialization of generic class

    ```Python
    from dataclasses import dataclass

    from managed import managed

    class Repo: ...

    @managed
    class PgRepo: ...

    @managed
    @dataclass
    class Service[R: Repo]:
        repo: R

    @managed
    @dataclass
    class App:
        svc: Service[PgRepo]
    ```
