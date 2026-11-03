"""Small typed result type for operations with expected failures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn


@dataclass(frozen=True, slots=True)
class Success[T]:
    """Successful result containing a value."""

    value: T

    @property
    def is_success(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_error(self) -> Exception:
        raise ValueError("A successful result has no error")

    def map[U](self, transform: Callable[[T], U]) -> Success[U]:
        return Success(transform(self.value))

    def map_error[Err: Exception, F: Exception](self, transform: Callable[[Err], F]) -> Success[T]:
        return self


@dataclass(frozen=True, slots=True)
class Failure[E: Exception]:
    """Failed result containing an expected exception."""

    error: E

    @property
    def is_success(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        raise self.error

    def unwrap_error(self) -> E:
        return self.error

    def map[T, U](self, transform: Callable[[T], U]) -> Failure[E]:
        return self

    def map_error[F: Exception](self, transform: Callable[[E], F]) -> Failure[F]:
        return Failure(transform(self.error))


type Result[T, E: Exception] = Success[T] | Failure[E]
