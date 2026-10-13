from typing import Any, Self

from .play import Play


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
