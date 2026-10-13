import random
import time

from ratingsystems.cer.model import ProbabilitySpace, Possession
from ratingsystems.cer.util.adjusted import AdjustedDistribution, AdjustedStat
from ratingsystems.cer.util.profile import profile
from ratingsystems.cer.util.statistics import NormalDistribution, SkewNormalDistribution


class RushYardsEngine():

    def __init__(
        self,
        plays,
        max_yards_lost: int = -5,
        max_yards_gained: int = 99,
        separate_redzone: bool = True,
        probability_cutoff: int = 0.00001,
        sampling_size: int = 1000,
    ):
        print("Creating Rushing Yards Engine ...")
        starttime = time.time()

        self.max_yards_lost = max_yards_lost
        self.max_yards_gained = max_yards_gained
        self.separate_redzone = separate_redzone
        self.probability_cutoff = probability_cutoff
        self.sampling_size = sampling_size

        plays = plays.filter(rushing=True)

        if self.separate_redzone:
            # Distribution of yards gained on rushing plays out of the redzone
            self.rush_yards = AdjustedDistribution.from_plays(
                plays.filter(yards_to_goal=lambda y: y > 20),
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )
            # Distribution of yards gained on rushing plays in the redzone
            self.redzone_rush_yards = AdjustedDistribution.from_plays(
                plays.filter(yards_to_goal=lambda y: y <= 20),
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )
        else:
            # Distribution of yards gained on rushing plays
            self.rush_yards = AdjustedDistribution.from_plays(
                plays,
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )

        print(f"Created Rushing Yards Engine after {time.time() - starttime} seconds")

    @profile
    def prime(self, possession: Possession):
        # Rushing stats
        rush_yards = self.rush_yards.distribution(
            offense=possession.offense,
            defense=possession.defense,
            sampling_size=self.sampling_size,
        )

        self.yards_gained = ProbabilitySpace()
        for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
            rush_odds = rush_yards.pdf(yards_gained)
            if rush_odds > self.probability_cutoff:
                self.yards_gained.add(rush_odds, yards_gained)

        self.yards_gained.normalize()

        if self.separate_redzone:
            # Redzone rushing stats
            rush_yards = self.redzone_rush_yards.distribution(
                offense=possession.offense,
                defense=possession.defense,
                sampling_size=self.sampling_size,
            )

            self.redzone_yards_gained = ProbabilitySpace()
            for yards_gained in range(self.max_yards_lost, 20):
                rush_odds = rush_yards.pdf(yards_gained)
                if rush_odds > self.probability_cutoff:
                    self.redzone_yards_gained.add(rush_odds, yards_gained)

            self.redzone_yards_gained.normalize()

    @profile
    def run(self, possession: Possession) -> ProbabilitySpace:
        if self.separate_redzone and possession.yards_to_goal <= 20:
            yards_gained = self.redzone_yards_gained.copy()
        else:
            yards_gained = self.yards_gained.copy()

        if possession.yards_to_goal - 99 > self.max_yards_lost:
            # Remove any yards lost that would result in a safety
            for y in range(self.max_yards_lost, possession.yards_to_goal - 99):
                yards_gained.remove(y)

            yards_gained.normalize()

        return yards_gained

    def simulate(self, possession: Possession) -> int:
        return round(self.possession_rush_yards.random())


class PassYardsEngine():

    def __init__(
        self,
        plays,
        max_yards_lost: int = -5,
        max_yards_gained: int = 99,
        separate_redzone: bool = True,
        probability_cutoff: int = 0.00001,
        sampling_size: int = 1000,
    ):
        print("Creating Passing Yards Engine ...")
        starttime = time.time()

        self.max_yards_lost = max_yards_lost
        self.max_yards_gained = max_yards_gained
        self.separate_redzone = separate_redzone
        self.probability_cutoff = probability_cutoff
        self.sampling_size = sampling_size

        plays = plays.filter(passing=True)

        if self.separate_redzone:
            # Distribution of yards gained on passing plays out of the redzone
            self.pass_yards = AdjustedDistribution.from_plays(
                plays.filter(yards_to_goal=lambda y: y > 20),
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )
            # Distribution of yards gained on passing plays in the redzone
            self.redzone_pass_yards = AdjustedDistribution.from_plays(
                plays.filter(yards_to_goal=lambda y: y <= 20),
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )

            # Percentage of completed passes out of the redzone
            self.completion_pct = AdjustedStat.from_plays(
                plays.filter(yards_to_goal=lambda y: y > 20),
                stat=lambda g: len(g.filter(passing_completed=True)) / len(g),
            )
            # Percentage of completed passes out of the redzone
            self.redzone_completion_pct = AdjustedStat.from_plays(
                plays.filter(yards_to_goal=lambda y: y <= 20),
                stat=lambda g: len(g.filter(passing_completed=True)) / len(g),
            )
        else:
            # Distribution of yards gained on passing plays
            self.pass_yards = AdjustedDistribution.from_plays(
                plays.filter(passing_completed=True),
                stat=lambda p: p.yards_gained,
                distribution_type=SkewNormalDistribution,
            )

            # Percentage of completed passes
            self.completion_pct = AdjustedStat.from_plays(
                plays,
                stat=lambda g: len(g.filter(passing_completed=True)) / len(g),
            )

        # Percentage of passing plays that end with a sack
        self.sack_pct = AdjustedStat.from_plays(
            plays,
            stat=lambda g: len(g.filter(sack=True)) / len(g),
        )

        # Distribution of yards gained on plays that end with a sack
        self.sack_yards = AdjustedDistribution.from_plays(
            plays.filter(sack=True),
            stat=lambda p: p.yards_gained,
            distribution_type=NormalDistribution,
        )

        print(f"Created Passing Yards Engine after {time.time() - starttime} seconds")

    @profile
    def prime(self, possession: Possession):
        # self.possession_pass_yards = self.pass_yards.distribution(
        #     offense=possession.offense,
        #     defense=possession.defense,
        #     sampling_size=self.sampling_size,
        # )
        # self.possession_sack_yards = self.sack_yards.distribution(
        #     offense=possession.offense,
        #     defense=possession.defense,
        #     sampling_size=self.sampling_size,
        # )
        # return

        # Passing stats
        completion_pct = self.completion_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )
        pass_yards = self.pass_yards.distribution(
            offense=possession.offense,
            defense=possession.defense,
            sampling_size=self.sampling_size,
        )
        sack_pct = self.sack_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )
        sack_yards = self.sack_yards.distribution(
            offense=possession.offense,
            defense=possession.defense,
            sampling_size=self.sampling_size,
        )
        incompletion_pct = 1 - completion_pct - sack_pct

        self.yards_gained = ProbabilitySpace()
        for yards_gained in range(self.max_yards_lost, self.max_yards_gained + 1):
            pass_odds = completion_pct * pass_yards.pdf(yards_gained) \
                      + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) \
                      + incompletion_pct * (1 if yards_gained == 0 else 0)
            if pass_odds > self.probability_cutoff:
                self.yards_gained.add(pass_odds, yards_gained)

        self.yards_gained.normalize()

        if self.separate_redzone:
            # Redzone passing stats
            completion_pct = self.redzone_completion_pct.value(
                offense=possession.offense,
                defense=possession.defense,
            )
            pass_yards = self.redzone_pass_yards.distribution(
                offense=possession.offense,
                defense=possession.defense,
                sampling_size=self.sampling_size,
            )

            self.redzone_yards_gained = ProbabilitySpace()
            for yards_gained in range(self.max_yards_lost, 20):
                pass_odds = completion_pct * pass_yards.pdf(yards_gained) \
                          + sack_pct * (sack_yards.pdf(yards_gained) if yards_gained < 0 else 0) \
                          + incompletion_pct * (1 if yards_gained == 0 else 0)
                if pass_odds > self.probability_cutoff:
                    self.redzone_yards_gained.add(pass_odds, yards_gained)

            self.redzone_yards_gained.normalize()

    @profile
    def run(self, possession: Possession) -> ProbabilitySpace:
        if self.separate_redzone and possession.yards_to_goal <= 20:
            yards_gained = self.redzone_yards_gained.copy()
        else:
            yards_gained = self.yards_gained.copy()

        if possession.yards_to_goal - 99 > self.max_yards_lost:
            # Remove any yards lost that would result in a safety
            for y in range(self.max_yards_lost, possession.yards_to_goal - 99):
                yards_gained.remove(y)

            yards_gained.normalize()

        return yards_gained

    def simulate(self, possession: Possession) -> int:
        completion_pct = self.completion_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )
        sack_pct = self.sack_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )

        r = random.random()
        if r <= completion_pct:
            return round(self.possession_pass_yards.random())

        elif r <= sack_pct + completion_pct:
            return round(self.possession_sack_yards.random())

        else:
            return 0
