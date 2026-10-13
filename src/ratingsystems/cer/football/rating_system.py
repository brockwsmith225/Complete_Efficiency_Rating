from statistics import fmean
from typing import Optional

from ratingsystems import Game, Rating, RatingSystem, Stat
from ratingsystems.core.util import FilterList

from ratingsystems.cer.football.calculator import (
    FieldGoalCalculator,
    KickoffCalculator,
    PenaltyCalculator,
    PuntCalculator,
    ScrimmageCalculator,
    TurnoverCalculator,
)
from ratingsystems.cer.football.epa import ExpectedPointsAddedRatingSystem


class FootballRatingSystem(RatingSystem):

    def __init__(
        self,
        recency_bias: float = 1.0,
        location_bias: float = 2.5, # about 4.5 is what the data shows (by points scored, home teams outscore equally matched away teams by about 2.5 points)
        competitive_bias: float = 5.0, # data isn't super strong, but maybe shows around 6.5, playing it safe rounding down to 5.0
    ):
        self.recency_bias = recency_bias
        self.location_bias = location_bias
        self.competitive_bias = competitive_bias

        self.rushing = ExpectedPointsAddedRatingSystem(
            ScrimmageCalculator(rushing=True),
            name="rushing",
            recency_bias=self.recency_bias,
            location_bias=self.location_bias,
            competitive_bias=self.competitive_bias,
        )
        self.passing = ExpectedPointsAddedRatingSystem(
            ScrimmageCalculator(passing=True),
            name="passing",
            recency_bias=self.recency_bias,
            location_bias=self.location_bias,
            competitive_bias=self.competitive_bias,
        )
        self.field_goals = ExpectedPointsAddedRatingSystem(
            FieldGoalCalculator(),
            name="_field_goals",
            recency_bias=self.recency_bias,
            location_bias=self.location_bias,
            competitive_bias=self.competitive_bias,
        )
        self.turnovers = ExpectedPointsAddedRatingSystem(
            TurnoverCalculator(),
            name="_turnovers",
            recency_bias=self.recency_bias,
            location_bias=-self.location_bias,  # negated because offense/defense are flipped
            competitive_bias=self.competitive_bias,
        )
        self.kickoffs = ExpectedPointsAddedRatingSystem(
            KickoffCalculator(),
            name="_kickoffs",
            recency_bias=self.recency_bias,
            location_bias=-self.location_bias,  # negated because offense/defense are flipped
            competitive_bias=self.competitive_bias,
        )
        self.punts = ExpectedPointsAddedRatingSystem(
            PuntCalculator(),
            name="_punts",
            recency_bias=self.recency_bias,
            location_bias=-self.location_bias,  # negated because offense/defense are flipped
            competitive_bias=self.competitive_bias,
        )

    def rate(self, games: list[Game]) -> Rating:
        # home_avg_points = fmean([g.home_points for g in games if not g.neutral_site and g.home_conference == g.away_conference])
        # away_avg_points = fmean([g.away_points for g in games if not g.neutral_site and g.home_conference == g.away_conference])
        # print(f"home: {home_avg_points}")
        # print(f"away: {away_avg_points}")
        # print(f"bias: {(home_avg_points - away_avg_points) / (home_avg_points + away_avg_points) * 100}")
        # return

        # teams = {}
        # for game in games:
        #     if game.postseason:
        #         continue
        #     if game.home_team not in teams:
        #         teams[game.home_team] = []
        #     if game.away_team not in teams:
        #         teams[game.away_team] = []
        #     teams[game.home_team].append(game)
        #     teams[game.away_team].append(game)

        # teams = {team: sorted(games, key=lambda g: g.week, reverse=True) for team, games in teams.items()}

        # # games_between = {}

        # # for team, games in teams.items():
        # #     for i in range(len(games)):
        # #         game_1 = games[i]
        # #         if team == game_1.home_team:
        # #             game_1_score = game_1.home_points - game_1.away_points
        # #         else:
        # #             game_1_score = game_1.away_points - game_1.home_points
        # #         for j in range(i+1, len(games)):
        # #             game_2 = games[j]
        # #             if team == game_1.home_team:
        # #                 game_2_score = game_2.home_points - game_2.away_points
        # #             else:
        # #                 game_2_score = game_2.away_points - game_2.home_points
        # #             if j - i not in games_between:
        # #                 games_between[j-i] = []
        # #             games_between[j-i].append(abs(game_1_score - game_2_score))

        # # for i, values in games_between.items():
        # #     print(f"{i},{fmean(values)}")

        # def calc_mov(game, team):
        #     if team == game.home_team:
        #         return game.home_points - game.away_points
        #     else:
        #         return game.away_points - game.home_points

        # for team, games in teams.items():
        #     for game in games:
        #         mov = calc_mov(game, team)
        #         movs = [calc_mov(g, team) for g in games if g.id != game.id and calc_mov(g, team) * mov > 0]
        #         if len(movs) == 0:
        #             continue
        #         average_mov = fmean(movs)
        #         print(f"{abs(mov)},{abs(average_mov)}")

        # return

        plays = FilterList([p for g in games for p in g.plays])

        avg_num_drives = fmean([
            len(game.split("drive_number"))
            for game in plays.split("game_id").values()
        ]) / 2

        teams = set(plays.split("offense").keys())

        play_types = set()

        def play_success_rate(play, team):
            if play.offense == team:
                value = rushing_engine.play_success_rate(play)
                if value is not None:
                    return value
                value = passing_engine.play_success_rate(play)
                if value is not None:
                    return value
                value = field_goal_engine.play_success_rate(play)
                if value is not None:
                    return value
                value = penalty_engine.play_success_rate(play)
                if value is not None:
                    return value
                play_types.add(play.play_type)
            elif play.defense == team:
                value = turnover_engine.play_success_rate(play)
                if value is not None:
                    return value
                value = kickoff_engine.play_success_rate(play)
                if value is not None:
                    return value
                value = punt_engine.play_success_rate(play)
                if value is not None:
                    return value
            return 0

        # for game in plays.filter(admin=False, other=False).split("game_id").values():
        #     for team in set(game.split("offense").keys()):
        #         print(f"{team},{sum([play_success_rate(p, team) for p in game])},{max([p.offense_score for p in game if p.offense == team])}")
        # raise Exception(f"{play_types}")
        
        rushing = self.rushing.rate(games)
        passing = self.passing.rate(games)

        offense = (rushing.offense + passing.offense) % "efficiency"

        defense = ~(rushing.defense + passing.defense) % "efficiency"

        field_goals = self.field_goals.rate(games)

        turnovers = -1 * self.turnovers.rate(games)

        kickoffs = self.kickoffs.rate(games)
        punts = self.punts.rate(games)

        coverage = ~(kickoffs.offense + punts.offense)
        returns = (kickoffs.defense + punts.defense)

        # TODO: defensive scores

        # TODO: penalties

        # TODO: time of controlling the ball?

        # TODO: scoring on kickoff/punt?

        # TODO: luck from things like fumble recoveries, opponent penalties, etc.

        offense = avg_num_drives * (offense + field_goals.offense + turnovers.defense + returns) % "offense"

        defense = ~(avg_num_drives * (defense + field_goals.defense + turnovers.offense + coverage)) % "defense"

        # TODO: separate turnovers back out for a separate rating?

        rating = (offense - defense) % "cer"

        # TODO: special teams rating should be based on how likely a field goal was to be made

        special_teams = avg_num_drives * (returns - coverage + field_goals.offense - field_goals.defense) % "special_teams"
        rating = rating << special_teams

        rating._avg_num_drives = avg_num_drives

        # TODO: tempo rating?

        return rating
