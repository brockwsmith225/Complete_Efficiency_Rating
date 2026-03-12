from typing import Any, Self

from .play import Play


class FilterDict:

    def __init__(self, objects: dict[str, Any]):
        self._objects = objects.copy()

    def filter(self, **kwargs) -> Self:
        # TODO: does this work nested?
        return FilterDict({key: obj for key, obj in self._objects.items() if obj.filter(**kwargs)})

    def split(self, *args) -> Self:
        pass

    def counts(self) -> dict[str, Any]:
        return {k: v.counts() if isinstance(v, FilterDict) else len(v) for k, v in self._objects.items()}

    def __iter__(self):
        for obj in self._objects.values():
            yield obj

    def items(self):
        return self._objects.items()

    def keys(self):
        return self._objects.keys()

    def __len__(self):
        return len(self._objects)


class FilterList:

    def __init__(self, objects: list[Any]):
        self._objects = objects.copy()

    def filter(self, **kwargs) -> Self:
        return FilterList([obj for obj in self._objects if all([getattr(obj, k) == v for k, v in kwargs.items()])])

    def split(self, key) -> FilterDict:
        objects = {}
        for obj in self._objects:
            if getattr(obj, key) not in objects:
                objects[getattr(obj, key)] = []
            objects[getattr(obj, key)].append(obj)
        objects = {k: FilterList(o) for k, o in objects.items()}
        return FilterDict(objects)

    def __iter__(self):
        for obj in self._objects:
            yield obj

    def __len__(self):
        return len(self._objects)

    def __add__(self, other):
        return FilterList(self._objects + other._objects)


class CFBTeam:

    def __init__(self, name: str, plays: FilterList):
        self.name = name
        self.plays = plays

    # @stat
    # @standarize
    def off_run_rate(self):
        return len(self.plays.filter(offense=self.name, rushing=True)) / len(self.plays.filter(offense=self.name, scrimmage=True))

    def off_pass_rate(self):
        return len(self.plays.filter(offense=self.name, passing=True)) / len(self.plays.filter(offense=self.name, scrimmage=True))


class Team:

    def __init__(self, name: str):
        self.name = name


class GameStats:

    def __init__(self, opponent: str, offense: dict[str, float], defense: dict[str, float]):
        self.offense = offense
        self.defense = defense

    def stats(self):
        return self.offense.keys()


class TeamStats:

    def __init__(self, name: str):
        self.name = name
        self.games = {}

    def opponents(self):
        pass

    @property
    def avg(self):
        self._offense = None
        return self._offense
