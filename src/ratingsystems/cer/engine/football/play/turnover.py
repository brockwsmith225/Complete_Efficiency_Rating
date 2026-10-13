import random
import time

from ratingsystems.cer.model import Possession
from ratingsystems.cer.util.adjusted import AdjustedStat
from ratingsystems.cer.util.profile import profile


class TurnoverEngine():

    def __init__(self, plays):
        print("Creating Turnover Engine ...")
        starttime = time.time()

        # Percentage of rushing plays that end with a fumble
        self.turnover_pct = AdjustedStat.from_plays(
            plays,
            stat=lambda g: len(g.filter(turnover=True)) / len(g),
        )

        print(f"Created Turnover Engine after {time.time() - starttime} seconds")

    @profile
    def run(self, possession: Possession) -> float:
        turnover_pct = self.turnover_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )
        return turnover_pct

    def simulate(self, possession: Possession) -> float:
        turnover_pct = self.turnover_pct.value(
            offense=possession.offense,
            defense=possession.defense,
        )
        return random.random() <= turnover_pct
