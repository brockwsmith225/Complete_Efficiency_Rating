from statistics import fmean, stdev
from typing import Any, Optional, Union

from ratingsystems.core.util.math import LinearRegression, linear_regression

from ratingsystems.cer.util.statistics import NormalDistribution


class LinearRegressionStat:

    def __init__(
        self,
        offense_models: dict[str, LinearRegression],
        defense_models: dict[str, LinearRegression],
        population_model: LinearRegression,
    ):
        self._offense_models = offense_models
        self._defense_models = defense_models
        self._population_model = population_model

    def value(
        self,
        *x: list[float],
        offense: Optional[str] = None,
        defense: Optional[str] = None,
    ) -> float:
        if offense is None and defense is None:
            return self._population_model(*x)
        if defense is None:
            return self._offense_models[offense](*x)
        elif offense is None:
            return self._defense_models[defense](*x)
        else:
            return (self._offense_models[offense](*x) + self._defense_models[defense](*x)) / 2

    @classmethod
    def from_plays(
        cls,
        plays: Any,
        input: str,
        target: callable[[Any], float],
        **kwargs,
    ) -> Self:
        offense_input_mapping = {
            team: team_plays.split(input)
            for team, team_plays in plays.split("offense").items()
        }
        offense_models = {
            team: LinearRegression.fit(
                [[input] for input in input_mapping.keys()],
                [
                    target(output)
                    for output in input_mapping.values()
                ],
                sample_weight=[len(output) for output in input_mapping.values()],
                **kwargs,
            )
            for team, input_mapping in offense_input_mapping.items()
        }

        defense_input_mapping = {
            team: team_plays.split(input)
            for team, team_plays in plays.split("defense").items()
        }
        defense_models = {
            team: LinearRegression.fit(
                [[input] for input in input_mapping.keys()],
                [
                    target(output)
                    for output in input_mapping.values()
                ],
                sample_weight=[len(output) for output in input_mapping.values()],
                **kwargs,
            )
            for team, input_mapping in defense_input_mapping.items()
        }

        population_input_mapping = plays.split(input)
        population_model = LinearRegression.fit(
            [[input] for input in population_input_mapping.keys()],
            [
                target(output)
                for output in population_input_mapping.values()
            ],
            sample_weight=[len(output) for output in population_input_mapping.values()],
            **kwargs,
        )

        return cls(
            offense_models=offense_models,
            defense_models=defense_models,
            population_model=population_model,
        )


class OpponentAdjustedLinearRegression():

    def __init__(
        self,
        offense_zscore_models: dict[str, LinearRegression],
        defense_zscore_models: dict[str, LinearRegression],
        offenses: dict[str, dict[float, NormalDistribution]],
        defenses: dict[str, dict[float, NormalDistribution]],
        population: dict[float, NormalDistribution],
        population_zscore_model: LinearRegression,
    ):
        self._offense_zscore_models = offense_zscore_models
        self._defense_zscore_models = defense_zscore_models
        self._offenses = offenses
        self._defenses = defenses
        self._population = population
        self._population_zscore_model = population_zscore_model

    def value(
        self,
        x: float,
        offense: Optional[str] = None,
        defense: Optional[str] = None,
    ) -> float:
        if offense is not None:
            offense_zscore = self._offense_zscore_models[offense](x)
            offense_distribution = self._offenses[offense][x]
        else:
            offense_zscore = 0
            offense_distribution = self._population[x]

        if defense is not None:
            defense_zscore = self._offense_zscore_models[defense](x)
            defense_distribution = self._defenses[defense][x]
        else:
            defense_zscore = 0
            defense_distribution = self._population[x]

        zscore = (offense_zscore + defense_zscore) / 2
        distribution = (offense_distribution + defense_distribution) / 2
        return distribution.value(zscore)

    @classmethod
    def from_plays(
        cls,
        plays: FilterList,
        input: str,
        input_range: list[float],
        target: callable[[Any], float],
        **kwargs,
    ) -> Self:
        offense_models = {
            team: {
                game[0].defense: LinearRegression.fit(
                    [[x] for x in game.split(input).keys()],
                    [
                        target(output)
                        for output in game.split(input).values()
                    ],
                    sample_weight=[len(output) for output in game.split(input).values()],
                    **kwargs,
                )
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("offense").items()
        }
        defense_models = {
            team: {
                game[0].offense: LinearRegression.fit(
                    [[x] for x in game.split(input).keys()],
                    [
                        target(output)
                        for output in game.split(input).values()
                    ],
                    sample_weight=[len(output) for output in game.split(input).values()],
                    **kwargs,
                )
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("defense").items()
        }

        # Collect each team's offensive distribution
        means = {
            team: {
                x: fmean([game(x) for game in games.values()])
                for x in input_range
            }
            for team, games in offense_models.items()
        }
        variances = {
            team: {
                x: stdev([game(x) for game in games.values()], xbar=means[team][x]) ** 2
                for x in input_range
            }
            for team, games in offense_models.items()
        }
        offenses = {
            team: {
                x: NormalDistribution(means[team][x], variances[team][x])
                for x in input_range
            }
            for team in offense_models.keys()
        }

        # Collect each team's defensive distribution
        means = {
            team: {
                x: fmean([game(x) for game in games.values()])
                for x in input_range
            }
            for team, games in defense_models.items()
        }
        variances = {
            team: {
                x: stdev([game(x) for game in games.values()], xbar=means[team][x]) ** 2
                for x in input_range
            }
            for team, games in defense_models.items()
        }
        defenses = {
            team: {
                x: NormalDistribution(means[team][x], variances[team][x])
                for x in input_range
            }
            for team in defense_models.keys()
        }

        # Collect each teams offensive zscore distributions measured against their opponents' defense
        zscores = {
            team: {
                x: fmean([defenses[opp][x].zscore(game(x)) for opp, game in games.items()])
                for x in input_range
            }
            for team, games in offense_models.items()
        }
        offense_zscore_models = {
            team: LinearRegression.fit(
                [[x] for x in zscore_mapping.keys()],
                [zscore for zscore in zscore_mapping.values()],
                **kwargs,
            )
            for team, zscore_mapping in zscores.items()
        }

        # Collect each teams defensive zscore distributions measured against their opponents' offense
        zscores = {
            team: {
                x: fmean([offenses[opp][x].zscore(game(x)) for opp, game in games.items()])
                for x in input_range
            }
            for team, games in defense_models.items()
        }
        defense_zscore_models = {
            team: LinearRegression.fit(
                [[x] for x in zscore_mapping.keys()],
                [zscore for zscore in zscore_mapping.values()],
                **kwargs,
            )
            for team, zscore_mapping in zscores.items()
        }

        models = [game for team in offense_models.values() for game in team.values()]
        pop_means = {
            x: fmean([model(x) for model in models])
            for x in input_range
        }
        pop_variances = {
            x: stdev([model(x) for model in models], xbar=pop_means[x]) ** 2
            for x in input_range
        }
        population = {
            x: NormalDistribution(pop_means[x], pop_variances[x])
            for x in input_range
        }
        zscore_mapping = {
            x: fmean([population[x].zscore(model(x)) for model in models])
            for x in input_range
        }
        population_zscore_model = LinearRegression.fit(
            [[x] for x in zscore_mapping.keys()],
            [zscore for zscore in zscore_mapping.values()],
            **kwargs,
        )

        return cls(
            offense_zscore_models,
            defense_zscore_models,
            offenses,
            defenses,
            population,
            population_zscore_model,
        )


