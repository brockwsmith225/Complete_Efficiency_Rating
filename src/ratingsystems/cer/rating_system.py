import math
from typing import Any, Optional

from ratingsystems import Rating, RatingSystem, Stat, TeamRating


class CompleteEfficiencyRatingSystem(RatingSystem):

    name: str = "cer"
    
    def __init__(self, include_points: bool = False):
        self.include_points = include_points

    def rate(self, games: list, seed: Rating = None) -> Rating:
        if seed is not None:
            seed = Rating.minmax_normalize(seed)

        teams = {}
        for game in games:
            if game.home_team not in teams:
                teams[game.home_team] = {
                    "opponents": [],
                    "points": [],
                    "possessions": [],
                    "points_per_possession": [],
                    "two_point_shot_percentage": [],
                    "two_point_shot_selection": [],
                    "three_point_shot_percentage": [],
                    "three_point_shot_selection": [],
                    "field_goal_shot_percentage": [],
                    "offensive_rebounds_percentage": [],
                    "turnovers_per_possession": [],
                    "free_throws_shot_percentage": [],
                    "free_throws_per_possession": [],
                    "possessions_allowed": [],
                    "points_per_possession_allowed": [],
                    "two_point_shot_percentage_allowed": [],
                    "two_point_shot_selection_allowed": [],
                    "three_point_shot_percentage_allowed": [],
                    "three_point_shot_selection_allowed": [],
                    "field_goal_shot_percentage_allowed": [],
                    "offensive_rebounds_percentage_allowed": [],
                    "turnovers_per_possession_allowed": [],
                    "free_throws_shot_percentage_allowed": [],
                    "free_throws_per_possession_allowed": [],
                }
            if game.away_team not in teams:
                teams[game.away_team] = {
                    "opponents": [],
                    "points": [],
                    "possessions": [],
                    "points_per_possession": [],
                    "two_point_shot_percentage": [],
                    "two_point_shot_selection": [],
                    "three_point_shot_percentage": [],
                    "three_point_shot_selection": [],
                    "field_goal_shot_percentage": [],
                    "offensive_rebounds_percentage": [],
                    "turnovers_per_possession": [],
                    "free_throws_shot_percentage": [],
                    "free_throws_per_possession": [],
                    "possessions_allowed": [],
                    "points_per_possession_allowed": [],
                    "two_point_shot_percentage_allowed": [],
                    "two_point_shot_selection_allowed": [],
                    "three_point_shot_percentage_allowed": [],
                    "three_point_shot_selection_allowed": [],
                    "field_goal_shot_percentage_allowed": [],
                    "offensive_rebounds_percentage_allowed": [],
                    "turnovers_per_possession_allowed": [],
                    "free_throws_shot_percentage_allowed": [],
                    "free_throws_per_possession_allowed": [],
                }
            if game.home_stats.field_goals_attempted:
                teams[game.home_team]["opponents"].append(game.away_team)
                teams[game.home_team]["points"].append(game.home_points)
                teams[game.home_team]["two_point_shot_percentage"].append(game.home_stats.two_point_field_goals_pct / 100.0)
                teams[game.home_team]["two_point_shot_selection"].append(game.home_stats.two_point_field_goals_attempted / game.home_stats.field_goals_attempted)
                teams[game.home_team]["three_point_shot_percentage"].append(game.home_stats.three_point_field_goals_pct / 100.0)
                teams[game.home_team]["three_point_shot_selection"].append(game.home_stats.three_point_field_goals_attempted / game.home_stats.field_goals_attempted)
                teams[game.home_team]["field_goal_shot_percentage"].append(game.home_stats.field_goals_pct / 100.0)
                teams[game.home_team]["offensive_rebounds_percentage"].append(game.home_stats.offensive_rebounds / (game.home_stats.offensive_rebounds + game.away_stats.defensive_rebounds))
                teams[game.home_team]["free_throws_shot_percentage"].append(game.home_stats.free_throws_pct / 100.0)
                teams[game.home_team]["two_point_shot_percentage_allowed"].append(game.away_stats.two_point_field_goals_pct / 100.0)
                teams[game.home_team]["two_point_shot_selection_allowed"].append(game.away_stats.two_point_field_goals_attempted / game.away_stats.field_goals_attempted)
                teams[game.home_team]["three_point_shot_percentage_allowed"].append(game.away_stats.three_point_field_goals_pct / 100.0)
                teams[game.home_team]["three_point_shot_selection_allowed"].append(game.away_stats.three_point_field_goals_attempted / game.away_stats.field_goals_attempted)
                teams[game.home_team]["field_goal_shot_percentage_allowed"].append(game.home_stats.field_goals_pct / 100.0)
                teams[game.home_team]["offensive_rebounds_percentage_allowed"].append(game.away_stats.offensive_rebounds / (game.away_stats.offensive_rebounds + game.home_stats.defensive_rebounds))
                teams[game.home_team]["free_throws_shot_percentage_allowed"].append(game.away_stats.free_throws_pct / 100.0)
                if game.home_stats.possessions:
                    team_possesions = game.home_stats.possessions
                    opponent_possessions = game.away_stats.possessions
                else:
                    # Estimate possessions when it's not an available stat
                    team_possesions = game.home_stats.field_goals_attempted - game.home_stats.offensive_rebounds + game.home_stats.turnovers + 0.4 * game.home_stats.free_throws_attempted
                    opponent_possessions = game.away_stats.field_goals_attempted - game.away_stats.offensive_rebounds + game.away_stats.turnovers + 0.4 * game.away_stats.free_throws_attempted
                teams[game.home_team]["possessions"].append(team_possesions)
                teams[game.home_team]["points_per_possession"].append(game.home_points / team_possesions)
                teams[game.home_team]["turnovers_per_possession"].append(game.home_stats.turnovers / team_possesions)
                teams[game.home_team]["free_throws_per_possession"].append(game.home_stats.free_throws_attempted / team_possesions)
                teams[game.home_team]["possessions_allowed"].append(opponent_possessions)
                teams[game.home_team]["points_per_possession_allowed"].append(game.away_points / opponent_possessions)
                teams[game.home_team]["turnovers_per_possession_allowed"].append(game.away_stats.turnovers / opponent_possessions)
                teams[game.home_team]["free_throws_per_possession_allowed"].append(game.away_stats.free_throws_attempted / opponent_possessions)
            if game.away_stats.field_goals_attempted:
                teams[game.away_team]["opponents"].append(game.home_team)
                teams[game.away_team]["points"].append(game.away_points)
                teams[game.away_team]["two_point_shot_percentage"].append(game.away_stats.two_point_field_goals_pct / 100.0)
                teams[game.away_team]["two_point_shot_selection"].append(game.away_stats.two_point_field_goals_attempted / game.away_stats.field_goals_attempted)
                teams[game.away_team]["three_point_shot_percentage"].append(game.away_stats.three_point_field_goals_pct / 100.0)
                teams[game.away_team]["three_point_shot_selection"].append(game.away_stats.three_point_field_goals_attempted / game.away_stats.field_goals_attempted)
                teams[game.away_team]["field_goal_shot_percentage"].append(game.away_stats.field_goals_pct / 100.0)
                teams[game.away_team]["offensive_rebounds_percentage"].append(game.away_stats.offensive_rebounds / (game.away_stats.offensive_rebounds + game.home_stats.defensive_rebounds))
                teams[game.away_team]["free_throws_shot_percentage"].append(game.away_stats.free_throws_pct / 100.0)
                teams[game.away_team]["two_point_shot_percentage_allowed"].append(game.home_stats.two_point_field_goals_pct / 100.0)
                teams[game.away_team]["two_point_shot_selection_allowed"].append(game.home_stats.two_point_field_goals_attempted / game.home_stats.field_goals_attempted)
                teams[game.away_team]["three_point_shot_percentage_allowed"].append(game.home_stats.three_point_field_goals_pct / 100.0)
                teams[game.away_team]["three_point_shot_selection_allowed"].append(game.home_stats.three_point_field_goals_attempted / game.home_stats.field_goals_attempted)
                teams[game.away_team]["field_goal_shot_percentage_allowed"].append(game.away_stats.field_goals_pct / 100.0)
                teams[game.away_team]["offensive_rebounds_percentage_allowed"].append(game.home_stats.offensive_rebounds / (game.home_stats.offensive_rebounds + game.away_stats.defensive_rebounds))
                teams[game.away_team]["free_throws_shot_percentage_allowed"].append(game.home_stats.free_throws_pct / 100.0)
                if game.away_stats.possessions:
                    team_possesions = game.away_stats.possessions
                    opponent_possessions = game.home_stats.possessions
                else:
                    # Estimate possessions when it's not an available stat
                    team_possesions = game.away_stats.field_goals_attempted - game.away_stats.offensive_rebounds + game.away_stats.turnovers + 0.4 * game.away_stats.free_throws_attempted
                    opponent_possessions = game.home_stats.field_goals_attempted - game.home_stats.offensive_rebounds + game.home_stats.turnovers + 0.4 * game.home_stats.free_throws_attempted
                teams[game.away_team]["possessions"].append(team_possesions)
                teams[game.away_team]["points_per_possession"].append(game.away_points / team_possesions)
                teams[game.away_team]["turnovers_per_possession"].append(game.away_stats.turnovers / team_possesions)
                teams[game.away_team]["free_throws_per_possession"].append(game.away_stats.free_throws_attempted / team_possesions)
                teams[game.away_team]["possessions_allowed"].append(opponent_possessions)
                teams[game.away_team]["points_per_possession_allowed"].append(game.home_points / opponent_possessions)
                teams[game.away_team]["turnovers_per_possession_allowed"].append(game.home_stats.turnovers / opponent_possessions)
                teams[game.away_team]["free_throws_per_possession_allowed"].append(game.home_stats.free_throws_attempted / opponent_possessions)
            # else:
            #     print("---------------------------------")
            #     print(f"{game.team} vs {game.opponent}")
            #     print(game)

        # Calculate season averages for each stat for each team
        for team in teams.values():
            for stat, values in team.copy().items():
                if stat == "opponents":
                    continue
                team[f"avg_{stat}"] = self._safe_average(values)
                team[f"stdev_{stat}"] = math.sqrt(self._safe_divide(sum([pow(v - team[f"avg_{stat}"], 2) for v in values]), len(values)))

        global_points = [value for team in teams for value in teams[team]["points"]]
        global_avg_points = self._safe_average(global_points)

        # How good are you at making 2 pointers
        two_point_shot_percentage = self._create_rating_from_stat(teams, "two_point_shot_percentage", name="_two_pct", games=games)
        # How many of your shots are 2 pointers
        two_point_shot_selection = self._create_rating_from_stat(teams, "two_point_shot_selection", name="_two_sel", games=games)
        # How good are you at making 3 pointers
        three_point_shot_percentage = self._create_rating_from_stat(teams, "three_point_shot_percentage", name="_three_pct", games=games)
        # How many of your shots are 3 pointers
        three_point_shot_selection = self._create_rating_from_stat(teams, "three_point_shot_selection", name="_three_sel", games=games)
        # Combined shooting rating
        shooting_rating = (two_point_shot_percentage * two_point_shot_selection * 2 + three_point_shot_percentage * three_point_shot_selection * 3) % "_shooting"

        # How often do you make shots (and therefore not have a chance for an offensive rebound)
        field_goal_shot_percentage = self._create_rating_from_stat(teams, "field_goal_shot_percentage", name="_shot_pct", games=games)
        # How often do you get an offensive rebound
        offensive_rebounds_percentage = self._create_rating_from_stat(teams, "offensive_rebounds_percentage", name="_pct", games=games)
        # Combined offensive rebounding percentage
        offensive_rebound_rating = (offensive_rebounds_percentage * (field_goal_shot_percentage * -1 + 1)) % "_rebounds"

        # How many possessions do you turn the ball over
        turnovers_per_possession = self._create_rating_from_stat(teams, "turnovers_per_possession", name="_turnovers", games=games)

        # How often do you get to the free throw line
        free_throws_per_possession = self._create_rating_from_stat(teams, "free_throws_per_possession", name="_per_poss", games=games)
        # How good are you at making free throws
        free_throw_shot_percentage = Rating({team: Stat(self._safe_average(stats["free_throws_shot_percentage"])) for team, stats in teams.items()}, name="_pct", games=games)
        free_throw_rating = (free_throws_per_possession * free_throw_shot_percentage) % "_free_throws"

        points_per_possession = self._create_rating_from_stat(teams, "points_per_possession", name="_points_per_poss", games=games)

        if self.include_points:
            offensive_efficiency = ((shooting_rating / (offensive_rebound_rating * -1 + 1) * (turnovers_per_possession * -1 + 1) + free_throw_rating) * points_per_possession) ** 0.5 % "_efficiency"
        else:
            offensive_efficiency = (shooting_rating / (offensive_rebound_rating * -1 + 1) * (turnovers_per_possession * -1 + 1) + free_throw_rating) % "_efficiency"
        offensive_rating = (offensive_efficiency / offensive_efficiency.mean * global_avg_points) % "offense"

        # How often do you let an opponent make a 2 pointer
        allowed_two_point_shot_percentage = self._create_rating_from_stat(teams, "two_point_shot_percentage_allowed", name="_two_pct", games=games)
        # How often does your opponent take a 2 pointer
        allowed_two_point_shot_selection = self._create_rating_from_stat(teams, "two_point_shot_selection_allowed", name="_two_sel", games=games)
        # How often do you let an opponent make a 3 pointer
        allowed_three_point_shot_percentage = self._create_rating_from_stat(teams, "three_point_shot_percentage_allowed", name="_three_pct", games=games)
        # How often does your opponent take a 3 pointer
        allowed_three_point_shot_selection = self._create_rating_from_stat(teams, "three_point_shot_selection_allowed", name="_three_sel", games=games)
        # Combined opponent shooting rating
        allowed_shooting_rating = (allowed_two_point_shot_percentage * allowed_two_point_shot_selection * 2 + allowed_three_point_shot_percentage * allowed_three_point_shot_selection * 3) % "_shooting"

        # How often do you let your opponent get an offensive rebound
        allowed_offensive_rebounds_percentage = self._create_rating_from_stat(teams, "offensive_rebounds_percentage_allowed", name="_rebounds", games=games)

        # How often does your opponent make shots (and therefore not have a chance for an offensive rebound)
        allowed_field_goal_shot_percentage = self._create_rating_from_stat(teams, "field_goal_shot_percentage_allowed", name="_shot_pct", games=games)
        # How often do you let your opponent get an offensive rebound
        allowed_offensive_rebounds_percentage = self._create_rating_from_stat(teams, "offensive_rebounds_percentage_allowed", name="_pct", games=games)
        # Combined opponent offensive rebounding percentage
        allowed_offensive_rebound_rating = (allowed_offensive_rebounds_percentage * (allowed_field_goal_shot_percentage * -1 + 1)) % "_rebounds"

        # How many turnovers do you force per possession
        forced_turnovers_per_possession = self._create_rating_from_stat(teams, "turnovers_per_possession_allowed", name="_turnovers", games=games)

        # How often do you put your opponent on the free throw line
        allowed_free_throws_per_possession = self._create_rating_from_stat(teams, "free_throws_per_possession_allowed", name="_per_poss", games=games)
        # How many free throws does an average team make
        global_free_throw_shot_percentage = self._safe_average([value for team in teams for value in teams[team]["free_throws_shot_percentage"]])
        # Combined opponent free throw rating
        allowed_free_throw_rating = (allowed_free_throws_per_possession * global_free_throw_shot_percentage) % "_free_throws"

        allowed_points_per_possession = self._create_rating_from_stat(teams, "points_per_possession_allowed", name="_points_per_poss", games=games)

        if self.include_points:
            defensive_efficiency = ((allowed_shooting_rating / (allowed_offensive_rebound_rating * -1 + 1) * (forced_turnovers_per_possession * -1 + 1) + allowed_free_throw_rating) * allowed_points_per_possession) ** 0.5 % "_efficiency"
        else:
            defensive_efficiency = (allowed_shooting_rating / (allowed_offensive_rebound_rating * -1 + 1) * (forced_turnovers_per_possession * -1 + 1) + allowed_free_throw_rating) % "_efficiency"
        defensive_rating = (defensive_efficiency / defensive_efficiency.mean * global_avg_points) % "defense"

        tempo_rating = self._create_rating_from_stat(teams, "possessions", name="tempo", games=games)

        return (offensive_rating - defensive_rating) % "cer" << tempo_rating

    @classmethod
    def _safe_divide(cls, x: float, y: float, default: float = 0.0) -> float:
        if y == 0:
            return default
        return x / y

    @classmethod
    def _safe_average(cls, x: list[float], default: float = 0.0) -> float:
        return cls._safe_divide(sum(x), len(x), default)

    @classmethod
    def _create_rating_from_stat(cls, teams: dict[str, dict[str, Any]], stat: str, **kwargs) -> Rating:
        global_values = [value for team in teams for value in teams[team][stat]]
        global_avg = cls._safe_average(global_values)
        global_stdev = math.sqrt(cls._safe_divide(sum([pow(v - global_avg, 2) for v in global_values]), len(global_values)))
        opposite_stat = stat.replace("_allowed", "") if stat.endswith("_allowed") else f"{stat}_allowed"
        return Rating({team: Stat(
            cls._safe_average([
                cls._zscore(v, teams[teams[team]["opponents"][i]][f"avg_{opposite_stat}"], teams[teams[team]["opponents"][i]][f"stdev_{opposite_stat}"]) for i, v in enumerate(teams[team][stat])
            ]) * global_stdev + global_avg
        ) for team in teams}, _averages={t: teams[t][f"avg_{stat}"] for t in teams}, _stdevs={t: teams[t][f"stdev_{stat}"] for t in teams}, _mean=global_avg, _stdev=global_stdev, **kwargs)

    @classmethod
    def _zscore(cls, value: float, mean: float, stdev: float) -> float:
        return (value - mean) / stdev