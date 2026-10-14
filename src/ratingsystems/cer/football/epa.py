import math
import numpy as np
from statistics import fmean
from typing import Callable, Optional

from ratingsystems import Game, Rating, RatingSystem, Stat
from ratingsystems.core.util import FilterList

from ratingsystems.cer.util.adjusted import AdjustedStat


class ExpectedPointsAddedRatingSystem(RatingSystem):

    def __init__(
        self,
        calculator: EPACalculator,
        name: Optional[str] = None,
        reverse_sort: bool = False,
        total: bool = False,
        recency_bias: float = 0.0,
        location_bias: float = 0.0, # about 4.5 is what the data shows (by points scored, home teams outscore equally matched away teams by about 2.5 points)
        competitive_bias: float = 0.0, # about _ is what the data shows (by points scored, )
    ):
        self.calculator = calculator
        self.name = name
        self.reverse_sort = reverse_sort
        self.total = total
        self.recency_bias = recency_bias
        self.location_bias = location_bias
        self.competitive_bias = competitive_bias

    def rate(self, games: list[Game]) -> Rating:
        game_order = {game.id: game.week + 100 if game.postseason else 0 for game in games}
        plays = FilterList(sorted([p for g in games for p in g.plays], key=lambda p: game_order[p.game_id]))
        teams = set(plays.split("offense").keys())

        if self.recency_bias:
            recency_weights = {}
            for game in sorted(games, key=lambda g: g.week + 100 if g.postseason else 0, reverse=True):
                if not game.plays:
                    continue
                if game.home_team not in recency_weights:
                    recency_weights[game.home_team] = []
                if game.away_team not in recency_weights:
                    recency_weights[game.away_team] = []
                recency_weights[game.home_team].append((1 - self.recency_bias / 100) ** len(recency_weights[game.home_team]))
                recency_weights[game.away_team].append((1 - self.recency_bias / 100) ** len(recency_weights[game.away_team]))
            recency_weights = {team: list(reversed(weights)) for team, weights in recency_weights.items()}
        else:
            recency_weights = None

        self.calculator.prime(plays)

        def num_of_drives(game: FilterList[Play]) -> int:
            # Count drives in the game but remove kickoffs as those have offense/defense backwards
            return len([d for d in game.split("drive_id").values() if all([not p.kickoff for p in d])])

        neutral_site_games = {g.id: g.neutral_site for g in games}

        def game_epa(game: FilterList[Play]) -> float:
            plays = [p for p in game if self.calculator(p) is not None]
            epas = [self.calculator(p) for p in plays]

            if self.location_bias and not neutral_site_games[game[0].game_id]:
                location_bias = self.location_bias / len(game)
                epas = [
                    epa - (
                        location_bias
                        if p.offense == p.home else
                        -location_bias
                    )
                    for epa, p in zip(epas, plays)
                ]

            if len(epas) == 0:
                return 0.0

            if self.competitive_bias:
                # TODO: do I care about time left in the game?
                # 2 score game is always competitive, that increases by number of quarters left
                #     (4th quarter = 2 scores, 3rd quarter = 3 scores, etc.)
                # competitiveness reduces for each score after the limit
                biases = [
                    (1 - self.competitive_bias / 100) **
                    max(math.ceil(abs(p.offense_score - p.defense_score) / 8) - (5 - p.period) - 1, 0)
                    for p in plays
                ]
                return float(np.average(epas, weights=biases))

            return fmean(epas)

        expected_points_added = AdjustedStat.from_plays(
            plays,
            stat=game_epa,
            weights=recency_weights,
        )

        num_plays_per_drive = AdjustedStat.from_plays(
            plays,
            stat=lambda game: sum([1 for p in game if self.calculator(p) is not None]) / num_of_drives(game),
            weights=recency_weights,
        )

        def predictor(offense: str, defense: str):
            # TODO: location bias?
            return expected_points_added.value(offense=offense, defense=defense) * num_plays_per_drive.value(offense=offense, defense=defense)

        offense_per_play = Rating(
            {team: Stat(expected_points_added.value(offense=team, defense=None)) for team in teams},
            games,
            name=self.name,
            reverse_sort=self.reverse_sort,
            _predictor=predictor,
        )

        num_plays = Rating(
            {team: Stat(num_plays_per_drive.value(offense=team, defense=None)) for team in teams},
            games,
        )

        offense = (offense_per_play * num_plays) % "offense"

        defense_per_play = Rating(
            {team: Stat(expected_points_added.value(offense=None, defense=team)) for team in teams},
            games,
            name=self.name,
            reverse_sort=not self.reverse_sort,
            _predictor=predictor
        )

        num_plays = Rating(
            {team: Stat(num_plays_per_drive.value(offense=None, defense=team)) for team in teams},
            games,
        )

        defense = (defense_per_play * num_plays) % "defense"

        rating = offense - defense
        rating.offense.name = None
        rating.defense.name = None

        rating._predcitor = predictor

        if self.reverse_sort:
            rating = ~rating

        return rating
