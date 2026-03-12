import multiprocessing
import time

from ratingsystems.cer.model import Possession


class _TurnoverEngine():

    def __init__(self, plays):
        print("Creating Turnover Engine ...")
        starttime = time.time()

        teams = set([p.offense for p in plays])

        # TODO: adjust by opponent?
        # TODO: safety?
        # TODO: defensive score?
        with multiprocessing.Pool(16) as pool:
            team_data = pool.starmap(self._extrapolate_team_data, [(team, "offense", plays.filter(offense=team)) for team in teams] + [(team, "defense", plays.filter(defense=team)) for team in teams])
            self.stats = {}
            for team, side, data in team_data:
                if team not in self.stats:
                    self.stats[team] = {}
                self.stats[team][side] = data

        print(f"Created Turnover Engine after {time.time() - starttime} seconds")

    def _extrapolate_team_data(self, name, side, team):
        data = {}
        data["fumble_pct"] = len(team.filter(fumble=True)) / len(team.filter(rushing=True))
        data["interception_pct"] = len(team.filter(interception=True)) / len(team.filter(passing=True))
        return name, side, data

    def run(self, possession: Possession):
        if possession.defense is None:
            fumble_pct = self.stats[possession.offense]["offense"]["fumble_pct"]
            interception_pct = self.stats[possession.offense]["offense"]["interception_pct"]
        elif possession.offense is None:
            fumble_pct = self.stats[possession.defense]["defense"]["fumble_pct"]
            interception_pct = self.stats[possession.defense]["defense"]["interception_pct"]
        else:
            fumble_pct = (self.stats[possession.offense]["offense"]["fumble_pct"] + self.stats[possession.defense]["defense"]["fumble_pct"]) / 2
            interception_pct = (self.stats[possession.offense]["offense"]["interception_pct"] + self.stats[possession.defense]["defense"]["interception_pct"]) / 2

        possession.fumble_pct = possession.rush_pct * fumble_pct
        possession.interception_pct = possession.pass_pct * interception_pct

        possession.turnover_pct = possession.fumble_pct + possession.interception_pct


class TurnoverEngine():

    def __init__(self, plays, possession: Possession):
        self.fumble_pct = len(possession.offense.filter(fumble=True)) / len(possession.offense.filter(rushing=True))
        self.interception_pct = len(possession.offense.filter(interception=True)) / len(possession.offense.filter(passing=True))

    def run(self, possession: Possession):
        possession.fumble_pct = possession.rush_pct * self.fumble_pct
        possession.interception_pct = possession.pass_pct * self.interception_pct
        possession.turnover_pct = possession.fumble_pct + possession.interception_pct
