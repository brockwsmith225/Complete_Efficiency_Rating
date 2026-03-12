import math
import multiprocessing
import time
from statistics import fmean, median, stdev
from scipy.stats import norm, skewnorm

from ratingsystems.common.util.math import linear_regression

from ratingsystems.cer.model import FilterList, ProbabilitySpace, Possession


class NormalDistribution():

    def __init__(self, mean: float, variance: float):
        self.mean = mean
        self.variance = abs(variance)

    @classmethod
    def fit(cls, data):
        result = norm.fit(data)
        mean = result[-2]
        variance = pow(result[-1], 2)
        return cls(
            mean=mean,
            variance=variance,
        )

    def pdf(self, value):
        return float(norm.pdf(value, loc=self.mean, scale=math.sqrt(self.variance)))

    def sampling(self, sampling_size: int = 1000) -> list[float]:
        return [float(x) for x in norm.rvs(loc=self.mean, scale=math.sqrt(self.variance), size=sampling_size)]

    def __str__(self):
        return f"({self.mean}, {self.variance})"

    def __repr__(self):
        return str(self)

    # TODO: math functions should follow real rules for Normal Distributions

    def __add__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean + other.mean, self.variance + other.variance)
        else:
            return NormalDistribution(self.mean + other, self.variance)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean - other.mean, self.variance - other.variance)
        else:
            return NormalDistribution(self.mean - other, self.variance)

    def __rsub__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean - self.mean, other.variance - self.variance)
        else:
            return NormalDistribution(other - self.mean, self.variance)

    def __mul__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean * other.mean, self.variance * other.variance)
        else:
            return NormalDistribution(self.mean * other, self.variance * abs(other))

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean / other.mean, self.variance / abs(other.variance))
        else:
            return NormalDistribution(self.mean / other, self.variance / abs(other))

    def __rtruediv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean / self.mean, abs(other.variance) / self.variance)
        else:
            return NormalDistribution(other / self.mean, abs(other) / self.variance)

    def __floordiv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean // other.mean, self.variance // abs(other.variance))
        else:
            return NormalDistribution(self.mean // other, self.variance // abs(other))

    def __rfloordiv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean // self.mean, abs(other.variance) // self.variance)
        else:
            return NormalDistribution(other // self.mean, abs(other) // self.variance)

    def __pow__(self, other):
        return NormalDistribution(math.pow(self.mean, other), math.pow(self.variance, other))

    def __eq__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean == other.mean and self.variance == other.variance
        else:
            return False

    def __le__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean <= other.mean
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean < other.mean
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean >= other.mean
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean > other.mean
        else:
            return False

    def __hash__(self):
        return hash((self.mean, self.variance))


class SkewNormalDistribution():

    def __init__(self, location: float, scale: float, shape: float):
        self.location = location
        self.scale = scale
        self.shape = shape

    # @property
    # def mean(self):
    #     return skewnorm.mean(a=self.shape, loc=self.location, scale=self.scale)

    # @property
    # def variance(self):
    #     return skewnorm.var(a=self.shape, loc=self.location, scale=self.scale)

    @classmethod
    def fit(cls, data: list[float]):
        shape, location, scale = skewnorm.fit(data)
        return cls(
            location=location,
            scale=scale,
            shape=shape,
        )

    def pdf(self, value: float):
        return float(skewnorm.pdf(value, a=self.shape, loc=self.location, scale=self.scale))

    def sampling(self, sampling_size: int = 1000) -> list[float]:
        return [float(x) for x in skewnorm.rvs(a=self.shape, loc=self.location, scale=self.scale, size=sampling_size)]


class _YardsEngine():
    """
    Calculates yards gained on a scrimmage play that does not result in a turnover or touchdown.

    Properties:
        yards_gained (ProbabilitySpace): each possible yards gained on the play and the corresponding probability
    """

    def __init__(self, plays, max_yards_lost: int = -25, max_yards_gained: int = 99, probability_cutoff: int = 0.00001):
        print("Creating Yards Engine ...")
        starttime = time.time()

        self.max_yards_lost = max_yards_lost
        self.max_yards_gained = max_yards_gained
        self.probability_cutoff = probability_cutoff

        # TODO: add skewness?

        games = plays.split("game_id")
        teams = {}
        for game in games:
            data = self._extrapolate_game_data(game)
            game_teams = list(data.keys())
            if game_teams[0] not in teams:
                teams[game_teams[0]] = []
            if game_teams[1] not in teams:
                teams[game_teams[1]] = []
            teams[game_teams[0]].append({
                "offense": data[game_teams[0]],
                "defense": data[game_teams[1]],
                "opponent": game_teams[1],
            })
            teams[game_teams[1]].append({
                "offense": data[game_teams[1]],
                "defense": data[game_teams[0]],
                "opponent": game_teams[0],
            })

        stats = {}
        self.means = {}
        self.stdevs = {}
        for t, team in teams.items():
            stats[t] = {
                "offense": {},
                "defense": {},
            }
            self.means[t] = {
                "offense": {},
                "defense": {},
            }
            self.stdevs[t] = {
                "offense": {},
                "defense": {},
            }
            for stat in ["rush_yards", "pass_yards", "sack_yards", "sack_pct", "incomplete_pct"]:
                stats[t]["offense"][stat] = {game["opponent"]: game["offense"][stat] for game in team if stat in game["offense"]}
                stats[t]["defense"][stat] = {game["opponent"]: game["defense"][stat] for game in team if stat in game["defense"]}
                if stat in ["rush_yards", "pass_yards", "sack_yards"]:
                    self.means[t]["offense"][stat] = NormalDistribution(
                        fmean([v.mean for v in stats[t]["offense"][stat].values()]),
                        fmean([v.variance for v in stats[t]["offense"][stat].values()])
                    )
                    self.means[t]["defense"][stat] = NormalDistribution(
                        fmean([v.mean for v in stats[t]["defense"][stat].values()]),
                        fmean([v.variance for v in stats[t]["defense"][stat].values()])
                    )
                    self.stdevs[t]["offense"][stat] = NormalDistribution(
                        stdev([v.mean for v in stats[t]["offense"][stat].values()], xbar=self.means[t]["offense"][stat].mean),
                        stdev([v.variance for v in stats[t]["offense"][stat].values()], xbar=self.means[t]["offense"][stat].variance)
                    )
                    self.stdevs[t]["defense"][stat] = NormalDistribution(
                        stdev([v.mean for v in stats[t]["defense"][stat].values()], xbar=self.means[t]["defense"][stat].mean),
                        stdev([v.variance for v in stats[t]["defense"][stat].values()], xbar=self.means[t]["defense"][stat].variance)
                    )
                else:
                    self.means[t]["offense"][stat] = fmean(stats[t]["offense"][stat].values())
                    self.means[t]["defense"][stat] = fmean(stats[t]["defense"][stat].values())
                    self.stdevs[t]["offense"][stat] = stdev(stats[t]["offense"][stat].values(), xbar=self.means[t]["offense"][stat])
                    self.stdevs[t]["defense"][stat] = stdev(stats[t]["defense"][stat].values(), xbar=self.means[t]["defense"][stat])


        self.means[None] = {
            "offense": {},
            "defense": {},
        }
        self.stdevs[None] = {
            "offense": {},
            "defense": {},
        }
        for stat in ["rush_yards", "pass_yards", "sack_yards", "sack_pct", "incomplete_pct"]:
            offense_stats = [value for team in stats.values() for value in team["offense"][stat].values()]
            defense_stats = [value for team in stats.values() for value in team["defense"][stat].values()]
            if stat in ["rush_yards", "pass_yards", "sack_yards"]:
                self.means[None]["offense"][stat] = NormalDistribution(
                    fmean([v.mean for v in offense_stats]),
                    fmean([v.variance for v in offense_stats])
                )
                self.means[None]["defense"][stat] = NormalDistribution(
                    fmean([v.mean for v in defense_stats]),
                    fmean([v.variance for v in defense_stats])
                )
                self.stdevs[None]["offense"][stat] = NormalDistribution(
                    stdev([v.mean for v in offense_stats], xbar=self.means[None]["offense"][stat].mean),
                    stdev([v.variance for v in offense_stats], xbar=self.means[None]["offense"][stat].variance)
                )
                self.stdevs[None]["defense"][stat] = NormalDistribution(
                    stdev([v.mean for v in defense_stats], xbar=self.means[None]["defense"][stat].mean),
                    stdev([v.variance for v in defense_stats], xbar=self.means[None]["defense"][stat].variance)
                )
            else:
                self.means[None]["offense"][stat] = fmean(offense_stats)
                self.means[None]["defense"][stat] = fmean(defense_stats)
                self.stdevs[None]["offense"][stat] = stdev(offense_stats, xbar=self.means[None]["offense"][stat])
                self.stdevs[None]["defense"][stat] = stdev(defense_stats, xbar=self.means[None]["defense"][stat])

        self.zscores = {}
        for t, team in teams.items():
            team = teams[t]
            self.zscores[t] = {
                "offense": {},
                "defense": {},
            }
            for stat in ["rush_yards", "pass_yards", "sack_yards", "sack_pct", "incomplete_pct"]:
                if stat in ["rush_yards", "pass_yards", "sack_yards"]:
                    self.zscores[t]["offense"][stat] = NormalDistribution(
                        fmean([(value.mean - self.means[opponent]["defense"][stat].mean) / self.stdevs[opponent]["defense"][stat].mean for opponent, value in stats[t]["offense"][stat].items()]),
                        fmean([(value.variance - self.means[opponent]["defense"][stat].variance) / self.stdevs[opponent]["defense"][stat].variance for opponent, value in stats[t]["offense"][stat].items()]),
                    )
                    self.zscores[t]["defense"][stat] = NormalDistribution(
                        fmean([(value.mean - self.means[opponent]["offense"][stat].mean) / self.stdevs[opponent]["offense"][stat].mean for opponent, value in stats[t]["defense"][stat].items()]),
                        fmean([(value.variance - self.means[opponent]["offense"][stat].variance) / self.stdevs[opponent]["offense"][stat].variance for opponent, value in stats[t]["defense"][stat].items()])
                    )
                else:
                    self.zscores[t]["offense"][stat] = fmean([(value - self.means[opponent]["defense"][stat]) / self.stdevs[opponent]["defense"][stat] for opponent, value in stats[t]["offense"][stat].items()])
                    self.zscores[t]["defense"][stat] = fmean([(value - self.means[opponent]["offense"][stat]) / self.stdevs[opponent]["offense"][stat] for opponent, value in stats[t]["defense"][stat].items()])

        # for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
        #     yards = NormalDistribution(
        #         self.zscores["Ohio State"]["offense"]["rush_yards"].mean * self.stdevs[None]["defense"]["rush_yards"].mean + self.means[None]["defense"]["rush_yards"].mean,
        #         self.zscores["Ohio State"]["offense"]["rush_yards"].variance * self.stdevs[None]["defense"]["rush_yards"].variance + self.means[None]["defense"]["rush_yards"].variance
        #     )
        #     odds = yards.pdf(yards_gained)
        #     if odds > self.probability_cutoff:
        #         print(f"{yards_gained},{odds}")

        # sack_pct = self.zscores["Ohio State"]["offense"]["sack_pct"] * self.stdevs[None]["defense"]["sack_pct"] + self.means[None]["defense"]["sack_pct"]
        # incomplete_pct = self.zscores["Ohio State"]["offense"]["incomplete_pct"] * self.stdevs[None]["defense"]["incomplete_pct"] + self.means[None]["defense"]["incomplete_pct"]
        # complete_pct = 1.0 - sack_pct - incomplete_pct
        # for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
        #     yards = NormalDistribution(
        #         self.zscores["Ohio State"]["offense"]["pass_yards"].mean * self.stdevs[None]["defense"]["pass_yards"].mean + self.means[None]["defense"]["pass_yards"].mean,
        #         self.zscores["Ohio State"]["offense"]["pass_yards"].variance * self.stdevs[None]["defense"]["pass_yards"].variance + self.means[None]["defense"]["pass_yards"].variance
        #     )
        #     sack_yards = NormalDistribution(
        #         self.zscores["Ohio State"]["offense"]["sack_yards"].mean * self.stdevs[None]["defense"]["sack_yards"].mean + self.means[None]["defense"]["sack_yards"].mean,
        #         self.zscores["Ohio State"]["offense"]["sack_yards"].variance * self.stdevs[None]["defense"]["sack_yards"].variance + self.means[None]["defense"]["sack_yards"].variance
        #     )
        #     odds = complete_pct * yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
        #     if odds > self.probability_cutoff:
        #         print(f"{yards_gained},{odds}")

        print(f"Created Yards Engine after {time.time() - starttime} seconds")

    def _extrapolate_game_data(self, game):
        teams = game.split("offense")
        data = {}
        for name, team in teams.items():
            data[name] = {}
            # TODO: split by down? passing by distance or yards_to_goal?
            scrimmage_plays = game.filter(scrimmage=True, turnover=False)

            rush_plays = scrimmage_plays.filter(rushing=True)
            rush_yards = [p.yards_gained for p in rush_plays]
            data[name]["rush_yards"] = SkewNormalDistribution.fit(rush_yards)

            pass_plays = scrimmage_plays.filter(passing=True)
            completed_pass_plays = pass_plays.filter(passing_completed=True)
            pass_yards = [p.yards_gained for p in completed_pass_plays]
            pass_mean = fmean(pass_yards)
            pass_stdev = stdev(pass_yards, xbar=pass_mean)
            data[name]["pass_yards"] = SkewNormalDistribution.fit(pass_yards)

            sack_plays = pass_plays.filter(sack=True)
            sack_yards = [p.yards_gained for p in sack_plays]
            sack_pct = len(sack_plays) / len(pass_plays)
            data[name]["sack_pct"] = sack_pct
            if len(sack_plays) > 0:
                sack_mean = fmean(sack_yards)
                sack_stdev = stdev(sack_yards, xbar=sack_mean) if len(sack_yards) > 1 else 0
                data[name]["sack_yards"] = NormalDistribution.fit(sack_yards)

            complete_pct = len(completed_pass_plays) / len(pass_plays)
            incomplete_pct = 1.0 - complete_pct - sack_pct
            data[name]["incomplete_pct"] = incomplete_pct
        return data

    def prime(self, possession: Possession):
        # print("Priming Yards Engine ...")
        # starttime = time.time()

        self.rush_probabilities = ProbabilitySpace()
        self.pass_probabilities = ProbabilitySpace()

        if possession.defense is None:
            rush_yards = NormalDistribution(
                self.zscores[possession.offense]["offense"]["rush_yards"].mean * self.stdevs[possession.defense]["defense"]["rush_yards"].mean + self.means[possession.defense]["defense"]["rush_yards"].mean,
                self.zscores[possession.offense]["offense"]["rush_yards"].variance * self.stdevs[possession.defense]["defense"]["rush_yards"].variance + self.means[possession.defense]["defense"]["rush_yards"].variance
            )

            sack_pct = self.zscores[possession.offense]["offense"]["sack_pct"] * self.stdevs[possession.defense]["defense"]["sack_pct"] + self.means[possession.defense]["defense"]["sack_pct"]
            incomplete_pct = self.zscores[possession.offense]["offense"]["incomplete_pct"] * self.stdevs[possession.defense]["defense"]["incomplete_pct"] + self.means[possession.defense]["defense"]["incomplete_pct"]
            complete_pct = 1.0 - sack_pct - incomplete_pct
            pass_yards = NormalDistribution(
                self.zscores[possession.offense]["offense"]["pass_yards"].mean * self.stdevs[possession.defense]["defense"]["pass_yards"].mean + self.means[possession.defense]["defense"]["pass_yards"].mean,
                self.zscores[possession.offense]["offense"]["pass_yards"].variance * self.stdevs[possession.defense]["defense"]["pass_yards"].variance + self.means[possession.defense]["defense"]["pass_yards"].variance
            )
            sack_yards = NormalDistribution(
                self.zscores[possession.offense]["offense"]["sack_yards"].mean * self.stdevs[possession.defense]["defense"]["sack_yards"].mean + self.means[possession.defense]["defense"]["sack_yards"].mean,
                self.zscores[possession.offense]["offense"]["sack_yards"].variance * self.stdevs[possession.defense]["defense"]["sack_yards"].variance + self.means[possession.defense]["defense"]["sack_yards"].variance
            )
            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = complete_pct * rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        elif possession.offense is None:
            rush_yards = NormalDistribution(
                self.zscores[possession.defense]["defense"]["rush_yards"].mean * self.stdevs[possession.offense]["offense"]["rush_yards"].mean + self.means[possession.offense]["offense"]["rush_yards"].mean,
                self.zscores[possession.defense]["defense"]["rush_yards"].variance * self.stdevs[possession.offense]["offense"]["rush_yards"].variance + self.means[possession.offense]["offense"]["rush_yards"].variance
            )

            sack_pct = self.zscores[possession.defense]["defense"]["sack_pct"] * self.stdevs[possession.offense]["offense"]["sack_pct"] + self.means[possession.offense]["offense"]["sack_pct"]
            incomplete_pct = self.zscores[possession.defense]["defense"]["incomplete_pct"] * self.stdevs[possession.offense]["offense"]["incomplete_pct"] + self.means[possession.offense]["offense"]["incomplete_pct"]
            complete_pct = 1.0 - sack_pct - incomplete_pct
            pass_yards = NormalDistribution(
                self.zscores[possession.defense]["defense"]["pass_yards"].mean * self.stdevs[possession.offense]["offense"]["pass_yards"].mean + self.means[possession.offense]["offense"]["pass_yards"].mean,
                self.zscores[possession.defense]["defense"]["pass_yards"].variance * self.stdevs[possession.offense]["offense"]["pass_yards"].variance + self.means[possession.offense]["offense"]["pass_yards"].variance
            )
            sack_yards = NormalDistribution(
                self.zscores[possession.defense]["defense"]["sack_yards"].mean * self.stdevs[possession.offense]["offense"]["sack_yards"].mean + self.means[possession.offense]["offense"]["sack_yards"].mean,
                self.zscores[possession.defense]["defense"]["sack_yards"].variance * self.stdevs[possession.offense]["offense"]["sack_yards"].variance + self.means[possession.offense]["offense"]["sack_yards"].variance
            )
            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = complete_pct * rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        else:
            rush_yards_mean_zscore = (self.zscores[possession.offense]["offense"]["rush_yards"].mean + self.zscores[possession.defense]["defense"]["rush_yards"].mean) / 2
            rush_yards_mean_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["rush_yards"].mean, 2) + pow(self.stdevs[possession.offense]["offense"]["rush_yards"].mean, 2)) / 2
            rush_yards_mean_mean = (self.means[possession.defense]["defense"]["rush_yards"].mean + self.means[possession.offense]["offense"]["rush_yards"].mean) / 2
            rush_yards_mean = rush_yards_mean_zscore * rush_yards_mean_stdev + stack_pct_mean

            rush_yards_variance_zscore = (self.zscores[possession.offense]["offense"]["rush_yards"].variance + self.zscores[possession.defense]["defense"]["rush_yards"].variance) / 2
            rush_yards_variance_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["rush_yards"].variance, 2) + pow(self.stdevs[possession.offense]["offense"]["rush_yards"].variance, 2)) / 2
            rush_yards_variance_mean = (self.means[possession.defense]["defense"]["rush_yards"].variance + self.means[possession.offense]["offense"]["rush_yards"].variance) / 2
            rush_yards_variance = rush_yards_mean_zscore * rush_yards_mean_stdev + stack_pct_mean

            rush_yards = NormalDistribution(
                rush_yards_mean,
                rush_yards_variance,
            )

            sack_pct_zscore = (self.zscores[possession.offense]["offense"]["sack_pct"] + self.zscores[possession.defense]["defense"]["sack_pct"]) / 2
            sack_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_pct"], 2) + pow(self.stdevs[possession.offense]["offense"]["sack_pct"], 2)) / 2
            sack_pct_mean = (self.means[possession.defense]["defense"]["sack_pct"] + self.means[possession.offense]["offense"]["sack_pct"]) / 2
            sack_pct = sack_pct_zscore * sack_pct_stdev + stack_pct_mean

            incomplete_pct_zscore = (self.zscores[possession.offense]["offense"]["incomplete_pct"] + self.zscores[possession.defense]["defense"]["incomplete_pct"]) / 2
            incomplete_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["incomplete_pct"], 2) + pow(self.stdevs[possession.offense]["offense"]["incomplete_pct"], 2)) / 2
            incomplete_pct_mean = (self.means[possession.defense]["defense"]["incomplete_pct"] + self.means[possession.offense]["offense"]["incomplete_pct"]) / 2
            incomplete_pct = incomplete_pct_zscore * incomplete_pct_stdev + stack_pct_mean

            complete_pct = 1.0 - sack_pct - incomplete_pct

            pass_yards_mean_zscore = (self.zscores[possession.offense]["offense"]["pass_yards"].mean + self.zscores[possession.defense]["defense"]["pass_yards"].mean) / 2
            pass_yards_mean_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["pass_yards"].mean, 2) + pow(self.stdevs[possession.offense]["offense"]["pass_yards"].mean, 2)) / 2
            pass_yards_mean_mean = (self.means[possession.defense]["defense"]["pass_yards"].mean + self.means[possession.offense]["offense"]["pass_yards"].mean) / 2
            pass_yards_mean = pass_yards_mean_zscore * pass_yards_mean_stdev + stack_pct_mean

            pass_yards_variance_zscore = (self.zscores[possession.offense]["offense"]["pass_yards"].variance + self.zscores[possession.defense]["defense"]["pass_yards"].variance) / 2
            pass_yards_variance_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["pass_yards"].variance, 2) + pow(self.stdevs[possession.offense]["offense"]["pass_yards"].variance, 2)) / 2
            pass_yards_variance_mean = (self.means[possession.defense]["defense"]["pass_yards"].variance + self.means[possession.offense]["offense"]["pass_yards"].variance) / 2
            pass_yards_variance = pass_yards_mean_zscore * pass_yards_mean_stdev + stack_pct_mean

            pass_yards = NormalDistribution(
                pass_yards_mean,
                pass_yards_variance,
            )

            sack_yards_mean_zscore = (self.zscores[possession.offense]["offense"]["sack_yards"].mean + self.zscores[possession.defense]["defense"]["sack_yards"].mean) / 2
            sack_yards_mean_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_yards"].mean, 2) + pow(self.stdevs[possession.offense]["offense"]["sack_yards"].mean, 2)) / 2
            sack_yards_mean_mean = (self.means[possession.defense]["defense"]["sack_yards"].mean + self.means[possession.offense]["offense"]["sack_yards"].mean) / 2
            sack_yards_mean = sack_yards_mean_zscore * sack_yards_mean_stdev + stack_pct_mean

            sack_yards_variance_zscore = (self.zscores[possession.offense]["offense"]["sack_yards"].variance + self.zscores[possession.defense]["defense"]["sack_yards"].variance) / 2
            sack_yards_variance_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_yards"].variance, 2) + pow(self.stdevs[possession.offense]["offense"]["sack_yards"].variance, 2)) / 2
            sack_yards_variance_mean = (self.means[possession.defense]["defense"]["sack_yards"].variance + self.means[possession.offense]["offense"]["sack_yards"].variance) / 2
            sack_yards_variance = sack_yards_mean_zscore * sack_yards_mean_stdev + stack_pct_mean

            sack_yards = NormalDistribution(
                sack_yards_mean,
                sack_yards_variance,
            )

            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = complete_pct * rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        self.rush_probabilities.normalize()
        self.pass_probabilities.normalize()

        # print(f"Primed Yards Engine after {time.time() - starttime} seconds")

    def run(self, possession: Possession):
        if possession.rush_pct + possession.pass_pct == 0:
            possession.yards_gained = ProbabilitySpace()
            return

        possession.yards_gained = self.rush_probabilities ** possession.rush_pct + self.pass_probabilities ** possession.pass_pct

        removed = False

        # Remove any yards lost that would result in a safety
        for yards_gained in range(self.max_yards_lost, possession.yards_to_goal - 99):
            possession.yards_gained.remove(yards_gained)
            removed = True

        # Remove any yards gained that would result in a touchdown
        for yards_gained in range(possession.yards_to_goal, self.max_yards_gained + 1):
            possession.yards_gained.remove(yards_gained)
            removed = True

        # TODO: turnover_on_downs_pct, this has to be normalized to rush_pct + pass_pct - turnover_pct - touchdown_pct

        if removed:
            possession.yards_gained.normalize()


class YardsEngineV2(_YardsEngine):

    def __init__(self, plays, max_yards_lost: int = -5, max_yards_gained: int = 99, probability_cutoff: int = 0.00001, sampling_size: int = 1000):
        print("Creating Yards Engine ...")
        starttime = time.time()

        self.max_yards_lost = max_yards_lost
        self.max_yards_gained = max_yards_gained
        self.probability_cutoff = probability_cutoff
        self.sampling_size = sampling_size

        # TODO: add skewness?

        games = plays.split("game_id")
        teams = {}
        for game in games:
            data = self._extrapolate_game_data(game)
            game_teams = list(data.keys())
            if game_teams[0] not in teams:
                teams[game_teams[0]] = []
            if game_teams[1] not in teams:
                teams[game_teams[1]] = []
            teams[game_teams[0]].append({
                "offense": data[game_teams[0]],
                "defense": data[game_teams[1]],
                "opponent": game_teams[1],
            })
            teams[game_teams[1]].append({
                "offense": data[game_teams[1]],
                "defense": data[game_teams[0]],
                "opponent": game_teams[0],
            })

        with multiprocessing.Pool(16) as pool:
            team_data = pool.starmap(self._extrapolate_team_data, [(team, "offense", plays.filter(offense=team)) for team in teams] + [(team, "defense", plays.filter(defense=team)) for team in teams])
            self.stats = {}
            for team, side, data in team_data:
                if team not in self.stats:
                    self.stats[team] = {}
                self.stats[team][side] = data

        stats = {}
        self.means = {}
        self.stdevs = {}
        for t, team in teams.items():
            stats[t] = {
                "offense": {},
                "defense": {},
            }
            self.means[t] = {
                "offense": {},
                "defense": {},
            }
            self.stdevs[t] = {
                "offense": {},
                "defense": {},
            }
            for stat in ["rush_yards", "pass_yards", "sack_yards", "sack_pct", "incomplete_pct"]:
                stats[t]["offense"][stat] = {game["opponent"]: game["offense"][stat] for game in team if stat in game["offense"]}
                stats[t]["defense"][stat] = {game["opponent"]: game["defense"][stat] for game in team if stat in game["defense"]}
                if stat in ["sack_pct", "incomplete_pct"]:
                    self.means[t]["offense"][stat] = fmean(stats[t]["offense"][stat].values())
                    self.means[t]["defense"][stat] = fmean(stats[t]["defense"][stat].values())
                    self.stdevs[t]["offense"][stat] = stdev(stats[t]["offense"][stat].values(), xbar=self.means[t]["offense"][stat])
                    self.stdevs[t]["defense"][stat] = stdev(stats[t]["defense"][stat].values(), xbar=self.means[t]["defense"][stat])


        self.means[None] = {
            "offense": {},
            "defense": {},
        }
        self.stdevs[None] = {
            "offense": {},
            "defense": {},
        }
        for stat in ["sack_pct", "incomplete_pct"]:
            offense_stats = [value for team in stats.values() for value in team["offense"][stat].values()]
            defense_stats = [value for team in stats.values() for value in team["defense"][stat].values()]
            self.means[None]["offense"][stat] = fmean(offense_stats)
            self.means[None]["defense"][stat] = fmean(defense_stats)
            self.stdevs[None]["offense"][stat] = stdev(offense_stats, xbar=self.means[None]["offense"][stat])
            self.stdevs[None]["defense"][stat] = stdev(defense_stats, xbar=self.means[None]["defense"][stat])

        self.zscores = {}
        for t, team in teams.items():
            team = teams[t]
            self.zscores[t] = {
                "offense": {},
                "defense": {},
            }
            for stat in ["sack_pct", "incomplete_pct"]:
                self.zscores[t]["offense"][stat] = fmean([(value - self.means[opponent]["defense"][stat]) / self.stdevs[opponent]["defense"][stat] for opponent, value in stats[t]["offense"][stat].items()])
                self.zscores[t]["defense"][stat] = fmean([(value - self.means[opponent]["offense"][stat]) / self.stdevs[opponent]["offense"][stat] for opponent, value in stats[t]["defense"][stat].items()])

        # self.differences = {}
        # for t, team in teams.items():
        #     team = teams[t]
        #     self.differences[t] = {
        #         "offense": {},
        #         "defense": {},
        #     }
        #     for stat in ["rush_yards", "pass_yards", "sack_yards"]:
        #         offense_samples = []
        #         defense_samples = []
        #         for opponent in stats[t]["offense"][stat].keys():
        #             team_offense_samples = stats[t]["offense"][stat][opponent].sampling(self.sampling_size)
        #             team_defense_samples = stats[t]["defense"][stat][opponent].sampling(self.sampling_size)
        #             opponent_offense_samples = self.stats[opponent]["offense"][stat].sampling(self.sampling_size)
        #             opponent_defense_samples = self.stats[opponent]["defense"][stat].sampling(self.sampling_size)
        #             offense_samples.append([team_offense_samples[i] - opponent_defense_samples[i] for i in range(self.sampling_size)])
        #             defense_samples.append([team_defense_samples[i] - opponent_offense_samples[i] for i in range(self.sampling_size)])
        #         self.differences[t]["offense"][stat] = NormalDistribution.fit(offense_samples)
        #         self.differences[t]["defense"][stat] = NormalDistribution.fit(defense_samples)

    def _extrapolate_team_data(self, name, side, team):
        data = {}
        scrimmage_plays = team.filter(scrimmage=True, turnover=False)
        scrimmage_plays = FilterList([p for p in scrimmage_plays if p.yards_gained >= self.max_yards_lost])
        rush_plays = scrimmage_plays.filter(rushing=True)
        data["rush_yards"] = SkewNormalDistribution.fit([p.yards_gained for p in rush_plays])
        pass_plays = scrimmage_plays.filter(passing=True, passing_completed=True)
        data["pass_yards"] = SkewNormalDistribution.fit([p.yards_gained for p in pass_plays])
        sack_plays = scrimmage_plays.filter(sack=True)
        data["sack_yards"] = NormalDistribution.fit([p.yards_gained for p in sack_plays])
        return name, side, data

    def prime(self, possession: Possession):
        # print("Priming Yards Engine ...")
        # starttime = time.time()

        self.rush_probabilities = ProbabilitySpace()
        self.pass_probabilities = ProbabilitySpace()

        if possession.defense is None:
            offense_samples = self.stats[possession.offense]["offense"]["rush_yards"].sampling(self.sampling_size)
            # defense_samples = self.stats[possession.defense]["defense"]["rush_yards"].sampling(self.sampling_size)
            rush_yards = SkewNormalDistribution.fit([offense_samples[i] for i in range(self.sampling_size)])

            sack_pct = self.zscores[possession.offense]["offense"]["sack_pct"] * self.stdevs[possession.defense]["defense"]["sack_pct"] + self.means[possession.defense]["defense"]["sack_pct"]
            incomplete_pct = self.zscores[possession.offense]["offense"]["incomplete_pct"] * self.stdevs[possession.defense]["defense"]["incomplete_pct"] + self.means[possession.defense]["defense"]["incomplete_pct"]
            complete_pct = 1.0 - sack_pct - incomplete_pct
            offense_samples = self.stats[possession.offense]["offense"]["pass_yards"].sampling(self.sampling_size)
            # defense_samples = self.stats[possession.defense]["defense"]["pass_yards"].sampling(self.sampling_size)
            pass_yards = SkewNormalDistribution.fit([offense_samples[i] for i in range(self.sampling_size)])
            offense_samples = self.stats[possession.offense]["offense"]["sack_yards"].sampling(self.sampling_size)
            # defense_samples = self.stats[possession.defense]["defense"]["sack_yards"].sampling(self.sampling_size)
            sack_yards = NormalDistribution.fit([offense_samples[i] for i in range(self.sampling_size)])

            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        elif possession.offense is None:
            # offense_samples = self.stats[possession.offense]["offense"]["rush_yards"].sampling(self.sampling_size)
            defense_samples = self.stats[possession.defense]["defense"]["rush_yards"].sampling(self.sampling_size)
            rush_yards = SkewNormalDistribution.fit([defense_samples[i] for i in range(self.sampling_size)])

            sack_pct = self.zscores[possession.defense]["defense"]["sack_pct"] * self.stdevs[possession.offense]["offense"]["sack_pct"] + self.means[possession.offense]["offense"]["sack_pct"]
            incomplete_pct = self.zscores[possession.defense]["defense"]["incomplete_pct"] * self.stdevs[possession.offense]["offense"]["incomplete_pct"] + self.means[possession.offense]["offense"]["incomplete_pct"]
            complete_pct = 1.0 - sack_pct - incomplete_pct
            # offense_samples = self.stats[possession.offense]["offense"]["pass_yards"].sampling(self.sampling_size)
            defense_samples = self.stats[possession.defense]["defense"]["pass_yards"].sampling(self.sampling_size)
            pass_yards = SkewNormalDistribution.fit([defense_samples[i] for i in range(self.sampling_size)])
            # offense_samples = self.stats[possession.offense]["offense"]["sack_yards"].sampling(self.sampling_size)
            defense_samples = self.stats[possession.defense]["defense"]["sack_yards"].sampling(self.sampling_size)
            sack_yards = NormalDistribution.fit([defense_samples[i] for i in range(self.sampling_size)])

            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        else:
            offense_samples = self.differences[possession.offense]["offense"]["rush_yards"].sampling(self.sampling_size)
            defense_samples = self.differences[possession.defense]["defense"]["rush_yards"].sampling(self.sampling_size)
            global_samples = self.means[possession.defense]["defense"]["rush_yards"].sampling(self.sampling_size)
            rush_yards = NormalDistribution.fit([offense_samples[i] + defense_samples[i] + global_samples[i] for i in range(self.sampling_size)])

            sack_pct_zscore = (self.zscores[possession.offense]["offense"]["sack_pct"] + self.zscores[possession.defense]["defense"]["sack_pct"]) / 2
            sack_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_pct"], 2) + pow(self.stdevs[possession.offense]["offense"]["sack_pct"], 2)) / 2
            sack_pct_mean = (self.means[possession.defense]["defense"]["sack_pct"] + self.means[possession.offense]["offense"]["sack_pct"]) / 2
            sack_pct = sack_pct_zscore * sack_pct_stdev + stack_pct_mean

            incomplete_pct_zscore = (self.zscores[possession.offense]["offense"]["incomplete_pct"] + self.zscores[possession.defense]["defense"]["incomplete_pct"]) / 2
            incomplete_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["incomplete_pct"], 2) + pow(self.stdevs[possession.offense]["offense"]["incomplete_pct"], 2)) / 2
            incomplete_pct_mean = (self.means[possession.defense]["defense"]["incomplete_pct"] + self.means[possession.offense]["offense"]["incomplete_pct"]) / 2
            incomplete_pct = incomplete_pct_zscore * incomplete_pct_stdev + stack_pct_mean

            complete_pct = 1.0 - sack_pct - incomplete_pct

            pass_yards_mean_zscore = (self.zscores[possession.offense]["offense"]["pass_yards"].mean + self.zscores[possession.defense]["defense"]["pass_yards"].mean) / 2
            pass_yards_mean_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["pass_yards"].mean, 2) + pow(self.stdevs[possession.offense]["offense"]["pass_yards"].mean, 2)) / 2
            pass_yards_mean_mean = (self.means[possession.defense]["defense"]["pass_yards"].mean + self.means[possession.offense]["offense"]["pass_yards"].mean) / 2
            pass_yards_mean = pass_yards_mean_zscore * pass_yards_mean_stdev + stack_pct_mean

            pass_yards_variance_zscore = (self.zscores[possession.offense]["offense"]["pass_yards"].variance + self.zscores[possession.defense]["defense"]["pass_yards"].variance) / 2
            pass_yards_variance_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["pass_yards"].variance, 2) + pow(self.stdevs[possession.offense]["offense"]["pass_yards"].variance, 2)) / 2
            pass_yards_variance_mean = (self.means[possession.defense]["defense"]["pass_yards"].variance + self.means[possession.offense]["offense"]["pass_yards"].variance) / 2
            pass_yards_variance = pass_yards_mean_zscore * pass_yards_mean_stdev + stack_pct_mean

            pass_yards = NormalDistribution(
                pass_yards_mean,
                pass_yards_variance,
            )

            sack_yards_mean_zscore = (self.zscores[possession.offense]["offense"]["sack_yards"].mean + self.zscores[possession.defense]["defense"]["sack_yards"].mean) / 2
            sack_yards_mean_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_yards"].mean, 2) + pow(self.stdevs[possession.offense]["offense"]["sack_yards"].mean, 2)) / 2
            sack_yards_mean_mean = (self.means[possession.defense]["defense"]["sack_yards"].mean + self.means[possession.offense]["offense"]["sack_yards"].mean) / 2
            sack_yards_mean = sack_yards_mean_zscore * sack_yards_mean_stdev + stack_pct_mean

            sack_yards_variance_zscore = (self.zscores[possession.offense]["offense"]["sack_yards"].variance + self.zscores[possession.defense]["defense"]["sack_yards"].variance) / 2
            sack_yards_variance_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"]["sack_yards"].variance, 2) + pow(self.stdevs[possession.offense]["offense"]["sack_yards"].variance, 2)) / 2
            sack_yards_variance_mean = (self.means[possession.defense]["defense"]["sack_yards"].variance + self.means[possession.offense]["offense"]["sack_yards"].variance) / 2
            sack_yards_variance = sack_yards_mean_zscore * sack_yards_mean_stdev + stack_pct_mean

            sack_yards = NormalDistribution(
                sack_yards_mean,
                sack_yards_variance,
            )

            for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
                rush_odds = rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.rush_probabilities.add(rush_odds, yards_gained)

                pass_odds = complete_pct * pass_yards.pdf(yards_gained) + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) + incomplete_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.pass_probabilities.add(pass_odds, yards_gained)

        self.rush_probabilities.normalize()
        self.pass_probabilities.normalize()


class YardsEngine():

    def __init__(self, plays, possession: Possession):
        scrimmage_plays = possession.offense.filter(scrimmage=True, turnover=False, scoring=False)

        rush_plays = scrimmage_plays.filter(rushing=True)
        rush_yards = [p.yards_gained for p in rush_plays]
        rush_mean = mean(rush_yards)
        rush_stdev = stdev(rush_yards, xbar=rush_mean)

        pass_plays = scrimmage_plays.filter(passing=True)
        completed_pass_plays = pass_plays.filter(passing_completed=True)
        pass_yards = [p.yards_gained for p in completed_pass_plays]
        pass_mean = mean(pass_yards)
        pass_stdev = stdev(pass_yards, xbar=pass_mean)

        sack_plays = pass_plays.filter(sack=True)
        sack_yards = [p.yards_gained for p in sack_plays]
        sack_pct = len(sack_plays) / len(pass_plays)
        sack_mean = mean(sack_yards)
        sack_stdev = stdev(sack_yards, xbar=sack_mean)

        complete_pct = len(completed_pass_plays) / len(pass_plays)
        incomplete_pct = 1.0 - complete_pct - sack_pct

        self.rush_odds = {}
        self.pass_odds = {}
        for yards_gained in range(-15, 100):
            self.rush_odds[yards_gained] = float(norm.pdf(yards_gained, rush_mean, rush_stdev))

            self.pass_odds[yards_gained] = complete_pct * float(norm.pdf(yards_gained, pass_mean, pass_stdev))
            if yards_gained < 0:
                self.pass_odds[yards_gained] += sack_pct * float(norm.pdf(yards_gained, sack_mean, sack_stdev))
            elif yards_gained == 0:
                self.pass_odds[yards_gained] += incomplete_pct

    def run(self, possession: Possession):
        if possession.rush_pct == 0 and possession.pass_pct == 0:
            possession.yards_gained = ProbabilitySpace()
            return
        # possession.yards_gained = ProbabilitySpace()

        # for yards_gained in range(max(-15, possession.yards_to_goal - 99), possession.yards_to_goal):
        #     rush_odds = self.rush_odds[yards_gained]

        #     pass_odds = self.pass_odds[yards_gained]

        #     odds = possession.rush_pct * rush_odds + possession.pass_pct * pass_odds
        #     if odds > 0:
        #         possession.yards_gained.add(odds, yards_gained)
        possession.yards_gained = ProbabilitySpace([(possession.rush_pct * self.rush_odds[yards_gained] + possession.pass_pct * self.pass_odds[yards_gained], yards_gained) for yards_gained in range(max(-15, possession.yards_to_goal - 99), possession.yards_to_goal)])
        possession.yards_gained.normalize(possession.rush_pct + possession.pass_pct - possession.fumble_pct - possession.interception_pct - possession.touchdown_pct)
