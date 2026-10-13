import numpy as np
from statistics import fmean, stdev
from typing import Any, Optional, Self, Type

from ratingsystems import Play
from ratingsystems.core.util import FilterList

from ratingsystems.cer.util.statistics import Distribution, NormalDistribution


def weighted_mean(values: list, weights: Optional[list] = None, team = None) -> float:
    try:
        return float(np.average(values, weights=weights))
    except Exception as e:
        print(team)
        print(values)
        print()
        print(weights)
        raise e


def weighted_variance(values: list, weights: Optional[list] = None, xbar: float = None) -> float:
    if xbar is None:
        xbar = weighted_mean(values, weights)
    return float(np.average((values - xbar) ** 2, weights=weights))


class AdjustedStat():

    def __init__(
        self,
        offense_zscores: dict[str, float],
        defense_zscores: dict[str, float],
        offenses: dict[str, NormalDistribution],
        defenses: dict[str, NormalDistribution],
        population: NormalDistribution,
    ):
        self._offense_zscores = offense_zscores
        self._defense_zscores = defense_zscores
        self._offenses = offenses
        self._defenses = defenses
        self._population = population

    def value(
        self,
        offense: Optional[str] = None,
        defense: Optional[str] = None,
    ) -> float:
        # TODO:
        #   one team - should I factor in their mean/stdev or just the global one? should the global one dilute the teams?
        #   two teams - which should it be:
        #     average zscores and global distributions
        #     average zscores and average distributions
        # z * stdev + mean = ((z1 + z2) / 2) * sqrt((var1 + var2) / 2) + ((mean1 + mean2) / 2)
        #                  = ((z1 + z2) * sqrt((var1 + var2) / 2) + (mean1 + mean2)) / 2
        #     zscores against opponent's distributions, average results
        # ((z1 * stdev2 + mean2) + (z2 * stdev1 + mean1)) / 2

        if offense is not None and defense is not None:
            # Being used for a matchup, this should average each team's zscore and measure
            # against the average of each team's distribution
            zscore = (self._offense_zscores[offense] + self._defense_zscores[defense]) / 2
            distribution = (self._offenses[offense] + self._defenses[defense]) / 2
            return distribution.value(zscore)

        else:
            # Being used for ratings, this should be the appropriate zscore measured against
            # the population's distribution
            if offense is not None:
                return self._population.value(self._offense_zscores[offense])
            elif defense is not None:
                return self._population.value(self._defense_zscores[defense])
            else:
                return self._population.value(0)

        # if offense is not None:
        #     offense_zscore = self._offense_zscores[offense]
        #     offense_distribution = self._offenses[offense]
        # else:
        #     offense_zscore = 0
        #     offense_distribution = self._population

        # if defense is not None:
        #     defense_zscore = self._defense_zscores[defense]
        #     defense_distribution = self._defenses[defense]
        # else:
        #     defense_zscore = 0
        #     defense_distribution = self._population

        # zscore = (offense_zscore + defense_zscore) / 2
        # distribution = (offense_distribution + defense_distribution) / 2
        # return distribution.value(zscore)

    @classmethod
    def from_stats(
        cls,
        offense_stats: dict[str, float],
        defense_stats: dict[str, float],
        weights: Optional[dict[str, float]] = None,
    ) -> Self:
        # TODO: weights on teams' distributions?

        # Collect each team's offensive distribution
        means = {
            team: fmean(games.values())
            for team, games in offense_stats.items()
        }
        variances = {
            team: stdev(games.values(), xbar=means[team]) ** 2 if len(games) > 1 else 0
            for team, games in offense_stats.items()
        }
        offenses = {
            team: NormalDistribution(means[team], variances[team])
            for team in offense_stats.keys()
        }

        # Collect each team's defensive distribution
        means = {
            team: fmean(games.values())
            for team, games in defense_stats.items()
        }
        variances = {
            team: stdev(games.values(), xbar=means[team]) ** 2 if len(games) > 1 else 0
            for team, games in defense_stats.items()
        }
        defenses = {
            team: NormalDistribution(means[team], variances[team])
            for team in defense_stats.keys()
        }

        if weights:
            offense_zscores = {
                team: weighted_mean([defenses[game[0]].zscore(value) for game, value in games.items()], weights[team], team)
                for team, games in offense_stats.items()
            }
        else:
            offense_zscores = {
                team: fmean([defenses[game[0]].zscore(value) for game, value in games.items()])
                for team, games in offense_stats.items()
            }

        if weights:
            defense_zscores = {
                team: weighted_mean([offenses[game[0]].zscore(value) for game, value in games.items()], weights[team], team)
                for team, games in defense_stats.items()
            }
        else:
            defense_zscores = {
                team: fmean([offenses[game[0]].zscore(value) for game, value in games.items()])
                for team, games in defense_stats.items()
            }

        values = [value for team in offense_stats.values() for value in team.values()]
        pop_mean = fmean(values)
        pop_variance = stdev(values, xbar=pop_mean) ** 2
        population = NormalDistribution(pop_mean, pop_variance)

        return cls(
            offense_zscores,
            defense_zscores,
            offenses,
            defenses,
            population,
        )

    @classmethod
    def from_plays(
        cls,
        plays: FilterList,
        stat: callable[[FilterList], float],
        weights: Optional[dict[str, float]] = None,
    ) -> Self:
        offense_stats = {
            team: {
                (game[0].defense, game[0].game_id): stat(game)
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("offense").items()
        }
        defense_stats = {
            team: {
                (game[0].offense, game[0].game_id): stat(game)
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("defense").items()
        }
        return cls.from_stats(
            offense_stats,
            defense_stats,
            weights,
        )

    @classmethod
    def _get_distribution(cls, values):
        mean = fmean(values)
        variance = stdev(values, xbar=mean) ** 2
        return NormalDistribution(mean, variance)


class AdjustedDistribution:

    def __init__(
        self,
        offense_zscore_distributions: dict[str, Distribution],
        defense_zscore_distributions: dict[str, Distribution],
        offenses: dict[str, NormalDistribution],
        defenses: dict[str, NormalDistribution],
        population: NormalDistribution,
        population_zscore_distribution: Distribution,
        distribution_type: Type[Distribution] = NormalDistribution,
    ):
        self._offense_zscore_distributions = offense_zscore_distributions
        self._defense_zscore_distributions = defense_zscore_distributions
        self._offenses = offenses
        self._defenses = defenses
        self._population = population
        self._population_zscore_distribution = population_zscore_distribution
        self._distribution_type = distribution_type

    def distribution(
        self,
        offense: Optional[str] = None,
        defense: Optional[str] = None,
        sampling_size: int = 1000,
    ) -> Distribution:
        if offense is not None and defense is not None:
            # Being used for a matchup, this should average each team's zscore distribution
            # and measure against the average of each team's distribution
            zscore_samples = self._offense_zscore_distributions[offense].sampling(sampling_size) \
                           + self._defense_zscore_distributions[defense].sampling(sampling_size)
            distribution = (self._offenses[offense] + self._defenses[defense]) / 2
            return self._distribution_type.fit([
                distribution.value(zscore)
                for zscore in zscore_samples
            ])

        else:
            # Being used for ratings, this should be the appropriate zscore measured against
            # the population's distribution
            # TODO: simplify and avoid resampling by supporting mult/add in SkewNormalDistribution class
            if offense is not None:
                return self._population.value(self._offense_zscore_distributions[offense])
                # return self._distribution_type.fit([
                #     self._population.value(zscore)
                #     for zscore in self._offense_zscore_distributions[offense].sampling(sampling_size)
                # ])
            elif defense is not None:
                return self._population.value(self._defense_zscore_distributions[defense])
                # return self._distribution_type.fit([
                #     self._population.value(zscore)
                #     for zscore in self._defense_zscore_distributions[defense].sampling(sampling_size)
                # ])
            else:
                return self._population.value(self._population_zscore_distribution)
                # return self._distribution_type.fit([
                #     self._population.value(zscore)
                #     for zscore in self._population_zscore_distribution.sampling(sampling_size)
                # ])


        # if offense is None and defense is None:
        #     return self._distribution_type.fit([
        #         self._population.value(zscore)
        #         for zscore in self._population_zscore_distribution.sampling(sampling_size)
        #     ])
        # elif defense is None:
        #     return self._distribution_type.fit([
        #         self._population.value(zscore)
        #         for zscore in self._offense_zscore_distributions[offense].sampling(sampling_size)
        #     ])
        # elif offense is None:
        #     return self._distribution_type.fit([
        #         self._population.value(zscore)
        #         for zscore in self._defense_zscore_distributions[defense].sampling(sampling_size)
        #     ])

        # if offense is not None:
        #     offense_zscore_distribution = self._offense_zscore_distributions[offense]
        #     offense_distribution = self._offenses[offense]
        # else:
        #     offense_zscore_distribution = self._population_zscore_distribution
        #     offense_distribution = self._population

        # if defense is not None:
        #     defense_zscore_distribution = self._defense_zscore_distributions[defense]
        #     defense_distribution = self._defenses[defense]
        # else:
        #     defense_zscore_distribution = self._population_zscore_distribution
        #     defense_distribution = self._population

        # # TODO: do I need to fit this distribution and then resample?
        # zscore_samples = offense_zscore_distribution.sampling(sampling_size) + defense_zscore_distribution.sampling(sampling_size)
        # distribution = (offense_distribution + defense_distribution) / 2
        # return self._distribution_type.fit([
        #     distribution.value(zscore)
        #     for zscore in zscore_samples
        # ])

    @classmethod
    def from_stats(
        cls,
        offense_stats: dict[str, float],
        defense_stats: dict[str, float],
        distribution_type: Type[Distribution],
    ) -> Self:
        # Collect each team's offensive distribution
        means = {
            team: fmean([value for game in games.values() for value in game])
            for team, games in offense_stats.items()
        }
        variances = {
            team: stdev([value for game in games.values() for value in game], xbar=means[team]) ** 2
            for team, games in offense_stats.items()
        }
        offenses = {
            team: NormalDistribution(means[team], variances[team])
            for team in offense_stats.keys()
        }

        # Collect each team's defensive distribution
        means = {
            team: fmean([value for game in games.values() for value in game])
            for team, games in defense_stats.items()
        }
        variances = {
            team: stdev([value for game in games.values() for value in game], xbar=means[team]) ** 2
            for team, games in defense_stats.items()
        }
        defenses = {
            team: NormalDistribution(means[team], variances[team])
            for team in defense_stats.keys()
        }

        # Collect each teams offensive zscore distributions measured against their opponents' defense
        offense_zscore_distributions = {
            team: distribution_type.fit(
                [defenses[game[0]].zscore(value) for game, values in games.items() for value in values]
            )
            for team, games in offense_stats.items()
        }

        # Collect each teams defensive zscore distributions measured against their opponents' offense
        defense_zscore_distributions = {
            team: distribution_type.fit(
                [offenses[game[0]].zscore(value) for game, values in games.items() for value in values]
            )
            for team, games in defense_stats.items()
        }

        values = [value for team in offense_stats.values() for game in team.values() for value in game]
        pop_mean = fmean(values)
        pop_variance = stdev(values, xbar=pop_mean) ** 2
        # pop_mean = fmean([o.mean for o in offenses.values()] + [d.mean for d in defenses.values()])
        # pop_variance = fmean([o.variance for o in offenses.values()] + [d.variance for d in defenses.values()])
        population = NormalDistribution(pop_mean, pop_variance)
        population_zscore_distribution = distribution_type.fit(
            [population.zscore(value) for value in values]
        )

        return cls(
            offense_zscore_distributions,
            defense_zscore_distributions,
            offenses,
            defenses,
            population,
            population_zscore_distribution,
            distribution_type,
        )

    @classmethod
    def from_plays(
        cls,
        plays: FilterList,
        stat: callable[[Play], float],
        distribution_type: Type[Distribution],
    ) -> Self:
        offense_stats = {
            team: {
                (game[0].defense, game[0].game_id): [stat(play) for play in game]
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("offense").items()
        }
        defense_stats = {
            team: {
                (game[0].offense, game[0].game_id): [stat(play) for play in game]
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("defense").items()
        }
        return cls.from_stats(
            offense_stats,
            defense_stats,
            distribution_type,
        )

    @classmethod
    def from_drives(
        cls,
        plays: FilterList,
        stat: callable[[FilterList[Play]], float],
        distribution_type: Type[Distribution],
    ) -> Self:
        offense_stats = {
            team: {
                (game[0].defense, game[0].game_id): [stat(drive) for drive in game.split("drive_id").values()]
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("offense").items()
        }
        defense_stats = {
            team: {
                (game[0].offense, game[0].game_id): [stat(drive) for drive in game.split("drive_id").values()]
                for game in plays.split("game_id").values()
            } for team, plays in plays.split("defense").items()
        }
        return cls.from_stats(
            offense_stats,
            defense_stats,
            distribution_type,
        )
