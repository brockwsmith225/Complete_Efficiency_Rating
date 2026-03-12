import functools
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProfileStats:
    count: int = 0
    total: float = 0
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def add(self, value: float):
        self.count += 1
        self.total += value
        if self.minimum is None or value < self.minimum:
            self.minimum = value
        if self.maximum is None or value > self.maximum:
            self.maximum = value

    @property
    def average(self) -> float:
        return self.total / self.count

    def __str__(self) -> str:
        return f"Count: {self.count}\nTotal: {self.total}\nAverage: {self.average}\nMinimum: {self.minimum}\nMaximum: {self.maximum}"

    def __repr__(self) -> str:
        return str(self)


class Profiler():

    def __init__(self):
        self.functions = {}

    def __call__(self, function):
        self.functions[function] = ProfileStats()
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            starttime = time.time()
            result = function(*args, **kwargs)
            duration = time.time() - starttime
            self.functions[function].add(duration)
            return result
        return wrapper

    def stats(self):
        for function, stats in self.functions.items():
            print(function)
            print(stats)

    def reset(self):
        for function, stats in self.functions.items():
            self.functions[function] = ProfileStats()


profile = Profiler()