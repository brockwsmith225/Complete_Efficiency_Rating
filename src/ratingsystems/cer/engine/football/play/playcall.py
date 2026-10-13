import random
import time
from dataclasses import dataclass
from typing import Optional

from ratingsystems.cer.model import Possession
from ratingsystems.cer.util.profile import profile
from ratingsystems.cer.util.stat import LinearRegressionStat


@dataclass
class Playcall:
    scrimmage_pct: float
    rush_pct: float
    pass_pct: float
    fga_pct: float
    punt_pct: float


class PlaycallEngine():

    def __init__(
        self,
        plays,
        max_distance: int = 20,
        degree: int = 1,
        log: bool = False,
        punt_limit: Optional[int] = 20,
        fga_limit: Optional[int] = 50,
    ):
        print("Creating Playcall Engine ...")
        starttime = time.time()

        self.max_distance = max_distance
        self.degree = degree
        self.log = log
        self.punt_limit = punt_limit
        self.fga_limit = fga_limit

        # Percent of scrimmage plays where the offense runs the ball, as a function of distance
        self.rush_pct = {
            down: LinearRegressionStat.from_plays(
                plays.filter(scrimmage=True, down=down),
                input="distance",
                target=lambda p: len(p.filter(rushing=True)) / len(p),
                degree=self.degree,
                log=self.log,
            )
            for down in range(1, 5)
        }

        # Percent of scrimmage plays where the offense throws the ball, as a function of distance
        self.pass_pct = {
            down: LinearRegressionStat.from_plays(
                plays.filter(scrimmage=True, down=down),
                input="distance",
                target=lambda p: len(p.filter(passing=True)) / len(p),
                degree=self.degree,
                log=self.log,
            )
            for down in range(1, 5)
        }

        # Percent of 4th downs where the offense goes for it, as a function of distance
        self.go_for_it_pct = LinearRegressionStat.from_plays(
            plays.filter(down=4),
            input="distance",
            target=lambda p: len(p.filter(scrimmage=True)) / len(p),
            degree=self.degree,
            log=self.log,
        )

        # Percent of 4th down special teams plays where the offense kicks a field goal, as a function of yards to goal
        self.fga_pct = LinearRegressionStat.from_plays(
            plays.filter(scrimmage=False, down=4),
            input="yards_to_goal",
            target=lambda p: len(p.filter(field_goal_attempt=True)) / len(p),
            degree=self.degree,
            log=self.log,
        )

        print(f"Created Playcall Engine after {time.time() - starttime} seconds")

    @profile
    def run(self, possession: Possession) -> Playcall:
        rush_pct = self.rush_pct[possession.down].value(possession.distance, offense=possession.offense)
        pass_pct = self.pass_pct[possession.down].value(possession.distance, offense=possession.offense)

        if rush_pct < 0:
            rush_pct = 0
        elif rush_pct > 1:
            rush_pct = 1
        if pass_pct < 0:
            pass_pct = 0
        elif pass_pct > 1:
            pass_pct = 1
        if rush_pct + pass_pct != 1:
            total = rush_pct + pass_pct
            rush_pct /= total
            pass_pct /= total

        if possession.down == 4:
            scrimmage_pct = self.go_for_it_pct.value(possession.distance, offense=possession.offense)
            if scrimmage_pct < 0:
                scrimmage_pct = 0
            elif scrimmage_pct > 1:
                scrimmage_pct = 1

            if self.fga_limit and possession.yards_to_goal > self.fga_limit:
                fga_pct = 0.0
                punt_pct = 1.0
            elif self.punt_limit and possession.yards_to_goal < self.punt_limit:
                fga_pct = 1.0
                punt_pct = 0.0
            else:
                fga_pct = self.fga_pct.value(possession.yards_to_goal, offense=possession.offense)
                punt_pct = 1.0 - fga_pct
        else:
            scrimmage_pct = 1.0
            punt_pct = 0.0
            fga_pct = 0.0

        return Playcall(
            scrimmage_pct=scrimmage_pct,
            rush_pct=rush_pct,
            pass_pct=pass_pct,
            fga_pct=fga_pct * (1 - scrimmage_pct),
            punt_pct=punt_pct * (1 - scrimmage_pct),
        )

    def simulate(self, possession: Possession) -> str:
        if possession.down == 4:
            scrimmage_pct = self.go_for_it_pct.value(possession.distance, offense=possession.offense)
            if scrimmage_pct < 0:
                scrimmage_pct = 0
            elif scrimmage_pct > 1:
                scrimmage_pct = 1

            if random.random() > scrimmage_pct:
                if self.fga_limit and possession.yards_to_goal > self.fga_limit:
                    return "punt"
                elif self.punt_limit and possession.yards_to_goal < self.punt_limit:
                    return "fga"
                else:
                    fga_pct = self.fga_pct.value(possession.yards_to_goal, offense=possession.offense)
                    if random.random() > fga_pct:
                        return "punt"
                    else:
                        return "fga"

        rush_pct = self.rush_pct[possession.down].value(possession.distance, offense=possession.offense)
        pass_pct = self.pass_pct[possession.down].value(possession.distance, offense=possession.offense)

        if rush_pct < 0:
            rush_pct = 0
        elif rush_pct > 1:
            rush_pct = 1
        if pass_pct < 0:
            pass_pct = 0
        elif pass_pct > 1:
            pass_pct = 1
        if rush_pct + pass_pct != 1:
            total = rush_pct + pass_pct
            rush_pct /= total
            pass_pct /= total

        if random.random() > rush_pct:
            return "pass"
        else:
            return "rush"
