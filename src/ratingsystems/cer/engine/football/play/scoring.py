import random
import time
from statistics import mean, median, stdev
from typing import Optional

from ratingsystems.core.util.math import linear_regression

from ratingsystems.cer.model import Possession
from ratingsystems.cer.util.adjusted import AdjustedStat
from ratingsystems.cer.util.profile import profile
from ratingsystems.cer.util.stat import LinearRegressionStat, OpponentAdjustedLinearRegression


class FieldGoalEngine():

    def __init__(
        self, 
        plays,
        degree: int = 1,
        log: bool = False,
    ):
        print("Creating Field Goal Engine ...")
        starttime = time.time()

        self.degree = degree
        self.log = log

        self.fgm_pct = LinearRegressionStat.from_plays(
            plays.filter(field_goal_attempt=True),
            input="yards_to_goal",
            target=lambda p: len(p.filter(field_goal_made=True)) / len(p),
            degree=self.degree,
            log=self.log,
        )

        print(f"Created Field Goal Engine after {time.time() - starttime} seconds")

    @profile
    def run(self, possession: Possession) -> float:
        fgm_pct = self.fgm_pct.value(
            possession.yards_to_goal,
            offense=possession.offense,
        )
        if fgm_pct < 0:
            fgm_pct = 0
        if fgm_pct > 1:
            fgm_pct = 1
        return fgm_pct

    def simulate(self, possession: Possession) -> bool:
        fgm_pct = self.fgm_pct.value(
            possession.yards_to_goal,
            offense=possession.offense,
        )
        return random.random() <= fgm_pct


class TouchdownEngine():

    def __init__(self, plays, degree: int = 1, log: bool = False):
        print("Creating Touchdown Engine ...")
        starttime = time.time()

        self.degree = degree
        self.log = log

        # TODO: cumulative?
        self.touchdown_pct = OpponentAdjustedLinearRegression.from_plays(
            plays,
            input="yards_to_goal",
            input_range=range(1, 21),
            target=lambda p: len(p.filter(scoring=True)) / len(p),
            degree=self.degree,
            log=self.log,
        )

        print(f"Created Touchdown Engine after {time.time() - starttime} seconds")

    def run(self, possession: Possession) -> float:        
        touchdown_pct = self.touchdown_pct.value(
            possession.yards_to_goal,
            offense=possession.offense,
            defense=possession.defense,
        )
        if touchdown_pct < 0:
            touchdown_pct = 0
        elif touchdown_pct > 1:
            touchdown_pct = 1
        return touchdown_pct

        # TODO: handle PAT
        # pat_pct = self.fgm_pct.value(
        #     2,
        #     offense=possession.offense
        # )
        # possession.pat_pct = possession.touchdown_pct * pat_pct
