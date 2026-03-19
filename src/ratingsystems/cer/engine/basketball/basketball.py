from functools import partial
from statistics import fmean
from typing import Callable

from ratingsystems import Game

from ratingsystems.cer.model import Possession
from ratingsystems.cer.engine.basketball.possession import FreeThrowEngine, ReboundEngine, ScoringEngine, TurnoverEngine


class BasketballEngine():

    def __init__(self, games: list[Game]):
        self.games = games

        self.scoring_engine = ScoringEngine(games)
        self.rebound_engine = ReboundEngine(games)
        self.turnover_engine = TurnoverEngine(games)
        self.free_throw_engine = FreeThrowEngine(games)

    def run(self, possession: Possession):
        self.scoring_engine.run(possession)
        self.rebound_engine.run(possession)
        self.turnover_engine.run(possession)
        self.free_throw_engine.run(possession)

        offensive_efficiency = possession
