import multiprocessing
import time
from statistics import fmean, median, stdev
from typing import Optional

from ratingsystems.common.util.math import linear_regression, logistic_regression

from ratingsystems.cer.model import FieldPosition, Possession
from ratingsystems.cer.model.util.filters import contains


class _Team():
    pass
    # offense {
    #     scrimmage {
    #         down {
    #             positions
    #             rush_pcts
    #             pass_pcts
    #             weights
    #         }
    #     }
    #     go_for_it {
    #         positions
    #         pcts
    #         weights
    #     }
    #     special {
    #         positions
    #         punt_pcts
    #         fga_pcts
    #         weights
    #     }
    # }

class Playcalls:

    def __init__(self):
        pass


class _PlaycallEngine():

    def __init__(self, plays, max_distance: int = 20, degree: int = 1, log: bool = False, punt_limit: Optional[int] = 20, fga_limit: Optional[int] = 50):
        print("Creating Playcall Engine ...")
        starttime = time.time()

        self.max_distance = max_distance
        self.degree = degree
        self.log = log
        self.punt_limit = punt_limit
        self.fga_limit = fga_limit

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
            for down in range(1, 5):
                stats[t]["offense"][down] = {}
                stats[t]["defense"][down] = {}
                self.means[t]["offense"][down] = {}
                self.means[t]["defense"][down] = {}
                self.stdevs[t]["offense"][down] = {}
                self.stdevs[t]["defense"][down] = {}
                for distance in range(1, 100):
                    stats[t]["offense"][down][distance] = {}
                    stats[t]["defense"][down][distance] = {}
                    self.means[t]["offense"][down][distance] = {}
                    self.means[t]["defense"][down][distance] = {}
                    self.stdevs[t]["offense"][down][distance] = {}
                    self.stdevs[t]["defense"][down][distance] = {}
                    for stat in ["rush_pct", "pass_pct"]:
                        stats[t]["offense"][down][distance][stat] = {game["opponent"]: game["offense"][down][distance][stat] for game in team if down in game["offense"] and distance in game["offense"][down] and stat in game["offense"][down][distance]}
                        stats[t]["defense"][down][distance][stat] = {game["opponent"]: game["defense"][down][distance][stat] for game in team if down in game["defense"] and distance in game["defense"][down] and stat in game["defense"][down][distance]}
                        self.means[t]["offense"][down][distance][stat] = fmean(stats[t]["offense"][down][distance][stat].values())
                        self.means[t]["defense"][down][distance][stat] = fmean(stats[t]["defense"][down][distance][stat].values())
                        self.stdevs[t]["offense"][down][distance][stat] = stdev(stats[t]["offense"][down][distance][stat].values(), xbar=self.means[t]["offense"][down][distance][stat])
                        self.stdevs[t]["defense"][down][distance][stat] = stdev(stats[t]["defense"][down][distance][stat].values(), xbar=self.means[t]["defense"][down][distance][stat])


        self.means[None] = {
            "offense": {},
            "defense": {},
        }
        self.stdevs[None] = {
            "offense": {},
            "defense": {},
        }
        for down in range(1, 5):
            self.means[None]["offense"][down] = {}
            self.means[None]["defense"][down] = {}
            self.stdevs[None]["offense"][down] = {}
            self.stdevs[None]["defense"][down] = {}
            for distance in range(1, 100):
                self.means[None]["offense"][down][distance] = {}
                self.means[None]["defense"][down][distance] = {}
                self.stdevs[None]["offense"][down][distance] = {}
                self.stdevs[None]["defense"][down][distance] = {}
                for stat in ["rush_pct", "pass_pct"]:
                    offense_stats = [value for team in stats.values() for value in team["offense"][down][distance][stat].values()]
                    defense_stats = [value for team in stats.values() for value in team["defense"][down][distance][stat].values()]
                    self.means[None]["offense"][down][distance][stat] = fmean(offense_stats)
                    self.means[None]["defense"][down][distance][stat] = fmean(defense_stats)
                    self.stdevs[None]["offense"][down][distance][stat] = stdev(offense_stats, xbar=self.means[None]["offense"][down][distance][stat])
                    self.stdevs[None]["defense"][down][distance][stat] = stdev(defense_stats, xbar=self.means[None]["defense"][down][distance][stat])

        self.zscores = {}
        for t, team in teams.items():
            team = teams[t]
            self.zscores[t] = {
                "offense": {},
                "defense": {},
            }
            for down in range(1, 5):
                self.zscores[t]["offense"][down] = {}
                self.zscores[t]["defense"][down] = {}
                for distance in range(1, 100):
                    self.zscores[t]["offense"][down][distance] = {}
                    self.zscores[t]["defense"][down][distance] = {}
                    for stat in ["rush_pct", "pass_pct"]:
                        self.zscores[t]["offense"][down][distance][stat] = fmean([(value - self.means[opponent]["defense"][down][distance][stat]) / self.stdevs[opponent]["defense"][down][distance][stat] if self.stdevs[opponent]["defense"][down][distance][stat] > 0 else 1.0 for opponent, value in stats[t]["offense"][down][distance][stat].items()])
                        self.zscores[t]["defense"][down][distance][stat] = fmean([(value - self.means[opponent]["offense"][down][distance][stat]) / self.stdevs[opponent]["offense"][down][distance][stat] if self.stdevs[opponent]["offense"][down][distance][stat] > 0 else 1.0 for opponent, value in stats[t]["defense"][down][distance][stat].items()])

        # for distance in range(1, 100):
        #     print(distance, end=",")
        #     for down in self.zscores["Ohio State"]["offense"]:
        #         print(self.zscores["Ohio State"]["offense"][down][distance]["rush_pct"] * self.stdevs[None]["offense"][down][distance]["rush_pct"] + self.means[None]["offense"][down][distance]["rush_pct"], end=",")
        #     print()

        # for yards_to_goal in range(1, 100):
        #     print(yards_to_goal, end=",")
        #     for down in [4]:
        #         print(self.stats["Ohio State"]["offense"][down][0][yards_to_goal]["fga_pct"], end=",")
        #     print()

        # for yards_to_goal in range(1, 100):
        #     print(yards_to_goal, end=",")
        #     for down in [4]:
        #         print(self.stats["Ohio State"]["offense"][down][3][yards_to_goal]["go_for_it_pct"], end=",")
        #     print()

        # for distance in range(1, 26):
        #     print(distance, end=",")
        #     for down in [4]:
        #         print(self.stats["Ohio State"]["offense"][down][distance][10]["go_for_it_pct"], end=",")
        #     print()

        print(f"Created Playcall Engine after {time.time() - starttime} seconds")

    def _extrapolate_game_data(self, game):
        teams = game.split("offense")
        data = {}
        for name, team in teams.items():
            data[name] = {}
            for down in range(1, 5):
                down_plays = team.filter(down=down)
                positions = []
                rush_pcts = []
                pass_pcts = []
                weights = []
                special_positions = []
                punt_pcts = []
                fga_pcts = []
                special_weights = []
                go_for_it_positions = []
                go_for_it_pcts = []
                go_for_it_weights = []
                for distance in range(1, self.max_distance + 1):
                    plays = down_plays.filter(distance=distance)
                    scrimmage_plays = plays.filter(scrimmage=True)
                    if len(scrimmage_plays) > 0:
                        positions.append([distance])
                        rush_pcts.append(len(scrimmage_plays.filter(rushing=True)) / len(scrimmage_plays))
                        pass_pcts.append(len(scrimmage_plays.filter(passing=True)) / len(scrimmage_plays))
                        weights.append(len(scrimmage_plays))

                data[name][down] = {}
                if len(positions) > 0:
                    rush_predictor = linear_regression(positions, rush_pcts, weights=weights, degree=self.degree, log=self.log)
                    pass_predictor = linear_regression(positions, pass_pcts, weights=weights, degree=self.degree, log=self.log)
                    for distance in range(1, 100):
                        rush_pct = rush_predictor(distance)
                        pass_pct = pass_predictor(distance)
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
                        data[name][down][distance] = {
                            "rush_pct": rush_pct,
                            "pass_pct": pass_pct,
                        }

        return data

    def _extrapolate_team_data(self, name, side, team):
        data = {
            4: {}
        }
        down_plays = team.filter(down=4)
        special_positions = []
        punt_pcts = []
        fga_pcts = []
        special_weights = []
        go_for_it_positions = []
        go_for_it_pcts = []
        go_for_it_weights = []
        for yards_to_goal in range(1, 100):
            plays = down_plays.filter(yards_to_goal=yards_to_goal)
            # special_plays = plays.filter(scrimmage=False)
            # if len(special_plays) > 0:
            #     special_positions.append([yards_to_goal])
            #     punt_pcts.append(len(special_plays.filter(punt=True)) / len(special_plays))
            #     fga_pcts.append(len(special_plays.filter(field_goal_attempt=True)) / len(special_plays))
            #     special_weights.append(len(special_plays))

            for distance in range(1, self.max_distance + 1):
                distance_plays = plays.filter(distance=distance)
                scrimmage_plays = distance_plays.filter(scrimmage=True)
                if len(distance_plays) > 0:
                    go_for_it_positions.append([distance, yards_to_goal])
                    go_for_it_pcts.append(len(scrimmage_plays) / len(distance_plays))
                    go_for_it_weights.append(len(distance_plays))

        for play in down_plays.filter(scrimmage=False):
            special_positions.append([play.yards_to_goal])
            punt_pcts.append(1 if play.punt else 0)
            fga_pcts.append(1 if play.field_goal_attempt else 0)
            special_weights.append(1)

        if len(special_positions) > 0:
            data[4][0] = {}
            # punt_predictor = linear_regression(special_positions, punt_pcts, weights=special_weights, degree=self.degree, log=self.log)
            # fga_predictor = linear_regression(special_positions, fga_pcts, weights=special_weights, degree=self.degree, log=self.log)
            punt_predictor = logistic_regression(special_positions, punt_pcts, weights=special_weights, degree=self.degree)
            fga_predictor = logistic_regression(special_positions, fga_pcts, weights=special_weights, degree=self.degree)
            for yards_to_goal in range(1, 100):
                if self.punt_limit and yards_to_goal <= self.punt_limit:
                    punt_pct = 0
                else:
                    punt_pct = punt_predictor(yards_to_goal)[1]
                if self.fga_limit and yards_to_goal >= self.fga_limit:
                    fga_pct = 0
                else:
                    fga_pct = fga_predictor(yards_to_goal)[1]
                if punt_pct < 0:
                    punt_pct = 0
                elif punt_pct > 1:
                    punt_pct = 1
                if fga_pct < 0:
                    fga_pct = 0
                elif fga_pct > 1:
                    fga_pct = 1
                if punt_pct + fga_pct != 1:
                    total = punt_pct + fga_pct
                    punt_pct /= total
                    fga_pct /= total
                data[4][0][yards_to_goal] = {
                    "punt_pct": punt_pct,
                    "fga_pct": fga_pct,
                }

        if len(go_for_it_positions) > 0:
            go_for_it_predictor = linear_regression(go_for_it_positions, go_for_it_pcts, weights=go_for_it_weights, degree=self.degree, log=self.log)
            for yards_to_goal in range(1, 100):
                for distance in range(1, yards_to_goal + 1):
                    if distance not in data[4]:
                        data[4][distance] = {}
                    go_for_it_pct = go_for_it_predictor(distance, yards_to_goal)
                    if go_for_it_pct < 0:
                        go_for_it_pct = 0
                    elif go_for_it_pct > 1:
                        go_for_it_pct = 1
                    data[4][distance][yards_to_goal] = {
                        "go_for_it_pct": go_for_it_pct,
                    }

        return name, side, data

    def run(self, possession: Possession):
        if possession.defense is None:
            rush_pct = self.zscores[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"] * self.stdevs[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"] + self.means[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"]
            pass_pct = self.zscores[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"] * self.stdevs[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"] + self.means[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"]

        elif possession.offense is None:
            rush_pct = self.zscores[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"] * self.stdevs[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"] + self.means[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"]
            pass_pct = self.zscores[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"] * self.stdevs[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"] + self.means[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"]

        else:
            rush_pct_zscore = (self.zscores[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"] + self.zscores[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"]) / 2
            rush_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"], 2) + pow(self.stdevs[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"], 2)) / 2
            rush_pct_mean = (self.means[possession.defense]["defense"][possession.down][possession.distance]["rush_pct"] + self.means[possession.offense]["offense"][possession.down][possession.distance]["rush_pct"]) / 2
            rush_pct = rush_pct_zscore * rush_pct_stdev + rush_pct_mean

            pass_pct_zscore = (self.zscores[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"] + self.zscores[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"]) / 2
            pass_pct_stdev = math.sqrt(pow(self.stdevs[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"], 2) + pow(self.stdevs[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"], 2)) / 2
            pass_pct_mean = (self.means[possession.defense]["defense"][possession.down][possession.distance]["pass_pct"] + self.means[possession.offense]["offense"][possession.down][possession.distance]["pass_pct"]) / 2
            pass_pct = pass_pct_zscore * pass_pct_stdev + pass_pct_mean

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
            scrimmage_pct = self.stats[possession.offense]["offense"][possession.down][possession.distance][possession.yards_to_goal]["go_for_it_pct"]
            punt_pct = self.stats[possession.offense]["offense"][possession.down][0][possession.yards_to_goal]["punt_pct"]
            fga_pct = self.stats[possession.offense]["offense"][possession.down][0][possession.yards_to_goal]["fga_pct"]
        else:
            scrimmage_pct = 1.0
            punt_pct = 0.0
            fga_pct = 0.0

        possession.scrimmage_pct = scrimmage_pct
        possession.rush_pct = rush_pct * scrimmage_pct
        possession.pass_pct = pass_pct * scrimmage_pct
        possession.punt_pct = punt_pct
        possession.fga_pct = fga_pct


class PlaycallEngine():

    def __init__(self, plays, possession: Possession, max_distance: int = 25, degree: int = 2, punt_limit: Optional[int] = 30, fga_limit: Optional[int] = 50):
        self.rush_predictors = {}
        self.pass_predictors = {}
        for down in range(1, 5):
            down_plays = possession.offense.filter(down=down)
            positions = []
            rush_pcts = []
            pass_pcts = []
            weights = []
            go_for_it_positions = []
            go_for_it_pcts = []
            go_for_it_weights = []
            special_positions = []
            punt_pcts = []
            fga_pcts = []
            special_weights = []
            for yards_to_goal in range(1, 100):
                for distance in range(1, min(max_distance + 1, yards_to_goal + 1)):
                    plays = down_plays.filter(yards_to_goal=yards_to_goal, distance=distance)
                    scrimmage_plays = plays.filter(scrimmage=True)
                    if len(scrimmage_plays) > 0:
                        positions.append([distance, yards_to_goal])
                        rush_pcts.append(len(scrimmage_plays.filter(rushing=True)) / len(scrimmage_plays))
                        pass_pcts.append(len(scrimmage_plays.filter(passing=True)) / len(scrimmage_plays))
                        weights.append(len(scrimmage_plays))
                    if down == 4 and len(plays) > 0:
                        go_for_it_positions.append([distance, yards_to_goal])
                        go_for_it_pcts.append(len(scrimmage_plays) / len(plays))
                        go_for_it_weights.append(len(plays))

                        num_special_plays = len(plays) - len(scrimmage_plays)
                        if num_special_plays > 0:
                            special_positions.append([yards_to_goal])
                            punt_pcts.append(len(plays.filter(punt=True)) / num_special_plays)
                            fga_pcts.append(len(plays.filter(field_goal_attempt=True)) / num_special_plays)
                            special_weights.append(num_special_plays)

            self.rush_predictors[down] = linear_regression(positions, rush_pcts, weights=weights, degree=degree)
            self.pass_predictors[down] = linear_regression(positions, pass_pcts, weights=weights, degree=degree)
            if down == 4:
                self.go_for_it_predictor = linear_regression(go_for_it_positions, go_for_it_pcts, weights=go_for_it_weights, degree=degree)
                if punt_limit:
                    self.punt_predictor = linear_regression(special_positions + [[punt_limit]], punt_pcts + [0], weights=special_weights + [1000], degree=degree)
                else:
                    self.punt_predictor = linear_regression(special_positions, punt_pcts, weights=special_weights)
                if fga_limit:
                    self.fga_predictor = linear_regression(special_positions + [[fga_limit]], fga_pcts + [0], weights=special_weights + [1000], degree=degree)
                else:
                    self.fga_predictor = linear_regression(special_positions, fga_pcts, weights=special_weights, degree=degree)

        self.punt_limit = punt_limit
        self.fga_limit = fga_limit

    def run(self, possession: Possession):
        if possession.down == 4:
            scrimmage_pct = self.go_for_it_predictor(possession.distance, possession.yards_to_goal)
            punt_pct = self.punt_predictor(possession.yards_to_goal)
            fga_pct = self.fga_predictor(possession.yards_to_goal)
            # if self.punt_limit and possession.yards_to_goal <= self.punt_limit:
            #     punt_pct = 0
            # if self.fga_limit and possession.yards_to_goal >= self.fga_limit:
            #     fga_pct = 0
            if scrimmage_pct < 0:
                scrimmage_pct = 0
            elif scrimmage_pct > 1:
                scrimmage_pct = 1
            if punt_pct < 0:
                punt_pct = 0
            elif punt_pct > 1:
                punt_pct = 1
            if fga_pct < 0:
                fga_pct = 0
            elif fga_pct > 1:
                fga_pct = 1
            if punt_pct + fga_pct != 1:
                total = punt_pct + fga_pct
                punt_pct /= total
                fga_pct /= total
            punt_pct = (1.0 - scrimmage_pct) * punt_pct
            fga_pct = (1.0 - scrimmage_pct) * fga_pct
        else:
            punt_pct = 0.0
            fga_pct = 0.0
            scrimmage_pct = 1.0

        rush_pct = self.rush_predictors[possession.down](possession.distance, possession.yards_to_goal)
        pass_pct = self.pass_predictors[possession.down](possession.distance, possession.yards_to_goal)

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

        rush_pct = scrimmage_pct * rush_pct
        pass_pct = scrimmage_pct * pass_pct

        possession.rush_pct = rush_pct
        possession.pass_pct = pass_pct
        possession.punt_pct = punt_pct
        possession.fga_pct = fga_pct
