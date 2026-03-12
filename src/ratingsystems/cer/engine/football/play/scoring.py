import multiprocessing
import time
from statistics import mean, median, stdev
from typing import Optional

from ratingsystems.common.util.math import linear_regression

from ratingsystems.cer.model import Possession


class _ScoringEngine():
    """
    Calculates probability of a touchdown on a scrimmage play or a field goal make on a field goal attempt.

    Properties:
        touchdown_pct (float): probability of a touchdown given a play from scrimmage is run
        fgm_pct (float): probability of a field goal make given a field goat is attempted
    """

    def __init__(self, plays, degree: int = 1, log: bool = False):
        print("Creating Scoring Engine ...")
        starttime = time.time()

        self.degree = degree
        self.log = log

        games = plays.split("game_id")
        teams = {}
        with multiprocessing.Pool(16) as pool:
            # for game in games:
            #     data = self._extrapolate_game_data(game)
            game_data = pool.map(self._extrapolate_game_data, games)
            for data in game_data:
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

            tasks = [(team, "offense", plays.filter(offense=team)) for team in teams.keys()] + [(team, "defense", plays.filter(defense=team)) for team in teams.keys()]
            tasks += [(None, "offense", plays), (None, "defense", plays)]
            team_data = pool.starmap(self._extrapolate_team_data, tasks)
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
            for yards_to_goal in range(1, 100):
                stats[t]["offense"][yards_to_goal] = {}
                stats[t]["defense"][yards_to_goal] = {}
                self.means[t]["offense"][yards_to_goal] = {}
                self.means[t]["defense"][yards_to_goal] = {}
                self.stdevs[t]["offense"][yards_to_goal] = {}
                self.stdevs[t]["defense"][yards_to_goal] = {}
                for stat in ["rush_td_pct", "pass_td_pct"]:
                    stats[t]["offense"][yards_to_goal][stat] = {game["opponent"]: game["offense"][yards_to_goal][stat] for game in team if yards_to_goal in game["offense"] and stat in game["offense"][yards_to_goal]}
                    stats[t]["defense"][yards_to_goal][stat] = {game["opponent"]: game["defense"][yards_to_goal][stat] for game in team if yards_to_goal in game["defense"] and stat in game["defense"][yards_to_goal]}
                    self.means[t]["offense"][yards_to_goal][stat] = mean(stats[t]["offense"][yards_to_goal][stat].values())
                    self.means[t]["defense"][yards_to_goal][stat] = mean(stats[t]["defense"][yards_to_goal][stat].values())
                    self.stdevs[t]["offense"][yards_to_goal][stat] = stdev(stats[t]["offense"][yards_to_goal][stat].values(), xbar=self.means[t]["offense"][yards_to_goal][stat])
                    self.stdevs[t]["defense"][yards_to_goal][stat] = stdev(stats[t]["defense"][yards_to_goal][stat].values(), xbar=self.means[t]["defense"][yards_to_goal][stat])


        self.means[None] = {
            "offense": {},
            "defense": {},
        }
        self.stdevs[None] = {
            "offense": {},
            "defense": {},
        }
        for yards_to_goal in range(1, 100):
            self.means[None]["offense"][yards_to_goal] = {}
            self.means[None]["defense"][yards_to_goal] = {}
            self.stdevs[None]["offense"][yards_to_goal] = {}
            self.stdevs[None]["defense"][yards_to_goal] = {}
            for stat in ["rush_td_pct", "pass_td_pct"]:
                offense_stats = [value for team in stats.values() for value in team["offense"][yards_to_goal][stat].values()]
                defense_stats = [value for team in stats.values() for value in team["defense"][yards_to_goal][stat].values()]
                self.means[None]["offense"][yards_to_goal][stat] = mean(offense_stats)
                self.means[None]["defense"][yards_to_goal][stat] = mean(defense_stats)
                self.stdevs[None]["offense"][yards_to_goal][stat] = stdev(offense_stats, xbar=self.means[None]["offense"][yards_to_goal][stat])
                self.stdevs[None]["defense"][yards_to_goal][stat] = stdev(defense_stats, xbar=self.means[None]["defense"][yards_to_goal][stat])

        self.zscores = {}
        for t, team in teams.items():
            team = teams[t]
            self.zscores[t] = {
                "offense": {},
                "defense": {},
            }
            for yards_to_goal in range(1, 100):
                self.zscores[t]["offense"][yards_to_goal] = {}
                self.zscores[t]["defense"][yards_to_goal] = {}
                for stat in ["rush_td_pct", "pass_td_pct"]:
                    self.zscores[t]["offense"][yards_to_goal][stat] = mean([(value - self.means[opponent]["defense"][yards_to_goal][stat]) / self.stdevs[opponent]["defense"][yards_to_goal][stat] if self.stdevs[opponent]["defense"][yards_to_goal][stat] > 0 else 1.0 for opponent, value in stats[t]["offense"][yards_to_goal][stat].items()])
                    self.zscores[t]["defense"][yards_to_goal][stat] = mean([(value - self.means[opponent]["offense"][yards_to_goal][stat]) / self.stdevs[opponent]["offense"][yards_to_goal][stat] if self.stdevs[opponent]["offense"][yards_to_goal][stat] > 0 else 1.0 for opponent, value in stats[t]["defense"][yards_to_goal][stat].items()])

        print(f"Created Scoring Engine after {time.time() - starttime} seconds")

    def _extrapolate_game_data(self, game):
        # TODO: determine if this is dependent on down and/or distance?
        teams = game.split("offense")
        data = {}
        for name, team in teams.items():
            data[name] = {}
            rush_positions = []
            rush_td_pcts = []
            rush_weights = []
            pass_positions = []
            pass_td_pcts = []
            pass_weights = []
            for yards_to_goal in range(1, 100):
                plays = team.filter(yards_to_goal=yards_to_goal)
                rushing_plays = plays.filter(rushing=True)
                passing_plays = plays.filter(passing=True)
                if len(rushing_plays) > 0:
                    rush_positions.append([yards_to_goal])
                    rush_td_pcts.append(len(rushing_plays.filter(scoring=True)) / len(rushing_plays))
                    rush_weights.append(len(rushing_plays))
                if len(passing_plays) > 0:
                    pass_positions.append([yards_to_goal])
                    pass_td_pcts.append(len(passing_plays.filter(scoring=True)) / len(passing_plays))
                    pass_weights.append(len(passing_plays))

            # TODO: logistic growth?
            if len(rush_positions) > 0:
                rush_td_predictor = linear_regression(rush_positions, rush_td_pcts, weights=rush_weights, degree=self.degree, log=self.log)
            else:
                rush_td_predictor = None

            if len(pass_positions) > 0:
                pass_td_predictor = linear_regression(pass_positions, pass_td_pcts, weights=pass_weights, degree=self.degree, log=self.log)
            else:
                pass_td_predictor = None

            for yards_to_goal in range(1, 100):
                rush_td_pct = rush_td_predictor(yards_to_goal) if rush_td_predictor else 0
                pass_td_pct = pass_td_predictor(yards_to_goal) if pass_td_predictor else 0
                if rush_td_pct < 0:
                    rush_td_pct = 0
                elif rush_td_pct > 1:
                    rush_td_pct = 1
                if pass_td_pct < 0:
                    pass_td_pct = 0
                elif pass_td_pct > 1:
                    pass_td_pct = 1
                data[name][yards_to_goal] = {
                    "rush_td_pct": rush_td_pct,
                    "pass_td_pct": pass_td_pct,
                }
        return data

    def _extrapolate_team_data(self, name, side, team):
        data = {}
        data["fgm_pct"] = len(team.filter(field_goal_made=True)) / len(team.filter(field_goal_attempt=True))
        return name, side, data

    def run(self, possession: Possession):
        if possession.defense is None:
            rush_td_pct = self.zscores[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"] * self.stdevs[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"] + self.means[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"]
            pass_td_pct = self.zscores[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"] * self.stdevs[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"] + self.means[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"]

        elif possession.offense is None:
            rush_td_pct = self.zscores[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"] * self.stdevs[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"] + self.means[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"]
            pass_td_pct = self.zscores[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"] * self.stdevs[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"] + self.means[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"]

        else:
            rush_td_pct_zscore = (self.zscores[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"] + self.zscores[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"]) / 2
            rush_td_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"], 2) + pow(self.stdevs[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"], 2)) / 2
            rush_td_pct_mean = (self.means[possession.defense]["defense"][possession.yards_to_goal]["rush_td_pct"] + self.means[possession.offense]["offense"][possession.yards_to_goal]["rush_td_pct"]) / 2
            rush_td_pct = rush_td_pct_zscore * rush_td_pct_stdev + rush_td_pct_mean

            pass_td_pct_zscore = (self.zscores[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"] + self.zscores[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"]) / 2
            pass_td_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"], 2) + pow(self.stdevs[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"], 2)) / 2
            pass_td_pct_mean = (self.means[possession.defense]["defense"][possession.yards_to_goal]["pass_td_pct"] + self.means[possession.offense]["offense"][possession.yards_to_goal]["pass_td_pct"]) / 2
            pass_td_pct = pass_td_pct_zscore * pass_td_pct_stdev + pass_td_pct_mean

        possession.touchdown_pct = possession.rush_pct * rush_td_pct + possession.pass_pct * pass_td_pct

        possession.fgm_pct = possession.fga_pct * self.stats[possession.offense]["offense"]["fgm_pct"]

        # TODO: handle PAT


class ScoringEngine():

    def __init__(self, plays, possession: Possession, max_distance: int = 25, degree: int = 1):
        self.rush_td_predictors = {}
        self.pass_td_predictors = {}
        for down in range(1, 5):
            down_rushing_plays = possession.offense.filter(down=down, turnover=False, rushing=True)
            down_passing_plays = possession.offense.filter(down=down, turnover=False, passing=True)
            rush_positions = []
            rush_td_pcts = []
            rush_weights = []
            pass_positions = []
            pass_td_pcts = []
            pass_weights = []
            for yards_to_goal in range(1, 100):
                for distance in range(1, min(max_distance + 1, yards_to_goal + 1)):
                    rushing_plays = down_rushing_plays.filter(yards_to_goal=yards_to_goal, distance=distance)
                    if len(rushing_plays) > 0:
                        rush_positions.append([distance, yards_to_goal])
                        rush_td_pcts.append(len(rushing_plays.filter(scoring=True)) / len(rushing_plays))
                        rush_weights.append(len(rushing_plays))

                    passing_plays = down_passing_plays.filter(yards_to_goal=yards_to_goal, distance=distance)
                    if len(passing_plays) > 0:
                        pass_positions.append([distance, yards_to_goal])
                        pass_td_pcts.append(len(passing_plays.filter(scoring=True)) / len(passing_plays))
                        pass_weights.append(len(passing_plays))

            self.rush_td_predictors = linear_regression(rush_positions, rush_td_pcts, weights=rush_weights, degree=degree)
            self.pass_td_predictors = linear_regression(pass_positions, pass_td_pcts, weights=pass_weights, degree=degree)

        # TODO: fgm pct by yards to goal
        self.fgm_pct = len(possession.offense.filter(field_goal_made=True)) / len(possession.offense.filter(field_goal_attempt=True))

    def run(self, possession: Possession):
        rush_td_pct = possession.rush_pct * self.rush_td_predictors[possession.down](possession.distance, possession.yards_to_goal)
        pass_td_pct = possession.pass_pct * self.pass_td_predictors[possession.down](possession.distance, possession.yards_to_goal)
        possession.touchdown_pct = rush_td_pct + pass_td_pct

        possession.fgm_pct = possession.fga_pct * self.fgm_pct

        # TODO: handle PAT
