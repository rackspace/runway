"""This type stub file was generated by pyright."""
# pylint: disable=C,E,W,R
from __future__ import annotations

from docker.types.base import DictType

class Healthcheck(DictType):
    def __init__(self, **kwargs) -> None: ...
    @property
    def test(self): ...
    @test.setter
    def test(self, value): ...
    @property
    def interval(self): ...
    @interval.setter
    def interval(self, value): ...
    @property
    def timeout(self): ...
    @timeout.setter
    def timeout(self, value): ...
    @property
    def retries(self): ...
    @retries.setter
    def retries(self, value): ...
    @property
    def start_period(self): ...
    @start_period.setter
    def start_period(self, value): ...