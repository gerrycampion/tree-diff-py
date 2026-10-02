from abc import abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseListMatcher(Generic[T]):
    @staticmethod
    @abstractmethod
    def match_lists(base: set[T], compare: set[T]) -> list[tuple[T, T]]:
        raise NotImplementedError