import random
import time
from statistics import median

from ratingsystems.cer.model import FieldPosition, Penalty, Possession, ProbabilitySpace
from ratingsystems.cer.util.adjusted import AdjustedStat
from ratingsystems.cer.util.profile import profile


class PenaltyEngine():

    # TODO: loss of down vs replay down penalties

    def __init__(self, plays):
        print("Creating Penalty Engine ...")
        starttime = time.time()

        # Percentage of plays that include a penalty on the offense
        # self.offense_penalty_pct = AdjustedStat.from_plays(
        #     plays,
        #     stat=lambda g: len([p for p in g.filter(penalty=True) if p.yards_gained < 0]) / len(g.filter(scrimmage=True)),
        # )

        # # Percentage of plays that include a penalty on the defense
        # self.defense_penalty_pct = AdjustedStat.from_plays(
        #     plays,
        #     stat=lambda g: len([p for p in g.filter(penalty=True) if p.yards_gained > 0]) / len(g.filter(scrimmage=True)),
        # )

        # TODO: deal with half the distance to goal penalties

        # self.offense_penalty_pcts = {
        #     yards: {
        #         lod: {
        #             team: len([p for p in team_plays.filter(penalty=True) if p.yards_gained == yards and p.loss_of_down == lod]) / len(team_plays.filter(scrimmage=True))
        #             for team, team_plays in plays.split("offense").items()
        #         }
        #         for lod in [False, True]
        #     }
        #     for yards in [-5, -10, -15]
        # }

        # self.defense_penalty_pcts = {
        #     yards: {
        #         firstdown: {
        #             team: len([p for p in team_plays.filter(penalty=True) if p.yards_gained == yards and p.loss_of_down == lod]) / len(team_plays.filter(scrimmage=True))
        #             for team, team_plays in plays.split("offense").items()
        #         }
        #         for firstdown in [False, True]
        #     }
        #     for yards in [5, 10, 15]
        # }

        self.offense_penalty_pct = {
            team: len([p for p in team_plays.filter(penalty=True) if p.yards_gained < 0]) / len(team_plays.filter(scrimmage=True))
            for team, team_plays in {**plays.split("offense"), **{None: plays}}.items()
        }
        self.offense_penalty_yards = {
            team: int(median([p.yards_gained for p in team_plays.filter(penalty=True) if p.yards_gained < 0]))
            for team, team_plays in {**plays.split("offense"), **{None: plays}}.items()
        }

        self.defense_penalty_pct = {
            team: len([p for p in team_plays.filter(penalty=True) if p.yards_gained > 0]) / len(team_plays.filter(scrimmage=True))
            for team, team_plays in {**plays.split("defense"), **{None: plays}}.items()
        }
        self.defense_penalty_yards = {
            team: int(median([p.yards_gained for p in team_plays.filter(penalty=True) if p.yards_gained > 0]))
            for team, team_plays in {**plays.split("defense"), **{None: plays}}.items()
        }

        print(f"Created Penalty Engine after {time.time() - starttime} seconds")

    @profile
    def run(self, possession: Possession) -> ProbabilitySpace:
        offense_penalty_pct = self.offense_penalty_pct[possession.offense]
        offense_penalty_yards = self.offense_penalty_yards[possession.offense]
        defense_penalty_pct = self.defense_penalty_pct[possession.defense]
        defense_penalty_yards = self.defense_penalty_yards[possession.defense]

        return ProbabilitySpace({
            Penalty(0, offense_penalty_yards): offense_penalty_pct,
            Penalty(0, defense_penalty_yards): defense_penalty_pct
        })

    # def simulate(self, possession: Possession) -> float:
    #     turnover_pct = self.turnover_pct.value(
    #         offense=possession.offense,
    #         defense=possession.defense,
    #     )
    #     return random.random() <= turnover_pct
