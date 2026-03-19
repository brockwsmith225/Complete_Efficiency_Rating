import math
import scipy.stats as st

from ratingsystems import Prediction, Predictor, Rating


class CompleteEfficiencyRatingPredictor(Predictor):

    name: str = "cer"

    def __init__(self, rating: Rating):
        if hasattr(rating, "cer"):
            rating = rating.cer
        super().__init__(rating)

    def predict(self, team: str, opponent: str) -> Prediction:
        team_two_point_shot_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._two_pct, team, self.rating.defense._efficiency._exp_points._two_pct, opponent)
        team_two_point_shot_selection = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._two_sel, team, self.rating.defense._efficiency._exp_points._two_sel, opponent)
        team_three_point_shot_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._three_pct, team, self.rating.defense._efficiency._exp_points._three_pct, opponent)
        team_three_point_shot_selection = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._three_sel, team, self.rating.defense._efficiency._exp_points._three_sel, opponent)
        team_expected_points = (team_two_point_shot_percentage * team_two_point_shot_selection * 2 + team_three_point_shot_percentage * team_three_point_shot_selection * 3) / (team_two_point_shot_selection + team_three_point_shot_selection)

        team_field_goal_shot_percentage = (team_two_point_shot_percentage * team_two_point_shot_selection + team_three_point_shot_percentage * team_three_point_shot_selection) / (team_two_point_shot_selection + team_three_point_shot_selection)
        team_offensive_rebounds_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._rebounds._pct, team, self.rating.defense._efficiency._rebounds._pct, opponent)
        team_offensive_rebounds_rating = team_offensive_rebounds_percentage * (1 - team_field_goal_shot_percentage)

        team_turnovers_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._turnovers, team, self.rating.defense._efficiency._turnovers, opponent)

        team_free_throws_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._free_throws._per_poss, team, self.rating.defense._efficiency._free_throws._per_poss, opponent)
        team_free_throw_shot_percentage = self.rating.offense._efficiency._free_throws._pct.get_value(team)
        team_free_throw_rating = team_free_throws_per_possession * team_free_throw_shot_percentage

        if hasattr(self.rating.offense._efficiency, "_points_per_poss"):
            team_points_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._points_per_poss, team, self.rating.defense._efficiency._points_per_poss, opponent)
            team_offensive_rating = ((team_expected_points / (1 - team_offensive_rebounds_rating) * (1 - team_turnovers_per_possession) * (1 - 0.44 * team_free_throws_per_possession) + team_free_throw_rating) * team_points_per_possession) ** 0.5
        else:
            team_offensive_rating = (team_expected_points / (1 - team_offensive_rebounds_rating) * (1 - team_turnovers_per_possession) * (1 - 0.44 * team_free_throws_per_possession) + team_free_throw_rating)

        opponent_two_point_shot_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._two_pct, opponent, self.rating.defense._efficiency._exp_points._two_pct, team)
        opponent_two_point_shot_selection = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._two_sel, opponent, self.rating.defense._efficiency._exp_points._two_sel, team)
        opponent_three_point_shot_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._three_pct, opponent, self.rating.defense._efficiency._exp_points._three_pct, team)
        opponent_three_point_shot_selection = self._calculate_matchup_value(self.rating.offense._efficiency._exp_points._three_sel, opponent, self.rating.defense._efficiency._exp_points._three_sel, team)
        opponent_expected_points = (opponent_two_point_shot_percentage * opponent_two_point_shot_selection * 2 + opponent_three_point_shot_percentage * opponent_three_point_shot_selection * 3) / (opponent_two_point_shot_selection + opponent_three_point_shot_selection)

        opponent_field_goal_shot_percentage = (opponent_two_point_shot_percentage * opponent_two_point_shot_selection + opponent_three_point_shot_percentage * opponent_three_point_shot_selection) / (opponent_two_point_shot_selection + opponent_three_point_shot_selection)
        opponent_offensive_rebounds_percentage = self._calculate_matchup_value(self.rating.offense._efficiency._rebounds._pct, opponent, self.rating.defense._efficiency._rebounds._pct, team)
        opponent_offensive_rebounds_rating = opponent_offensive_rebounds_percentage * (1 - opponent_field_goal_shot_percentage)

        opponent_turnovers_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._turnovers, opponent, self.rating.defense._efficiency._turnovers, team)

        opponent_free_throws_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._free_throws._per_poss, opponent, self.rating.defense._efficiency._free_throws._per_poss, team)
        opponent_free_throw_shot_percentage = self.rating.offense._efficiency._free_throws._pct.get_value(opponent)
        opponent_free_throw_rating = opponent_free_throws_per_possession * opponent_free_throw_shot_percentage

        if hasattr(self.rating.offense._efficiency, "_points_per_poss"):
            opponent_points_per_possession = self._calculate_matchup_value(self.rating.offense._efficiency._points_per_poss, opponent, self.rating.defense._efficiency._points_per_poss, team)
            opponent_offensive_rating = ((opponent_expected_points / (1 - opponent_offensive_rebounds_rating) * (1 - opponent_turnovers_per_possession) * (1 - 0.44 * opponent_free_throws_per_possession) + opponent_free_throw_rating) * opponent_points_per_possession) ** 0.5
        else:
            opponent_offensive_rating = (opponent_expected_points / (1 - opponent_offensive_rebounds_rating) * (1 - opponent_turnovers_per_possession) * (1 - 0.44 * opponent_free_throws_per_possession) + opponent_free_throw_rating)

        tempo = self._calculate_matchup_value(self.rating.tempo, team, self.rating.tempo, opponent)

        team_score = team_offensive_rating * tempo
        opponent_score = opponent_offensive_rating * tempo

        # TODO: calculate odds by 1/2/3 standard deviations in either direction??

        return Prediction(
            team,
            opponent,
            line=team_score - opponent_score,
            odds=st.norm.cdf((team_score - opponent_score) / self.rating.confidence_interval),
            team_score=team_score,
            opponent_score=opponent_score,
        )

    @classmethod
    def _calculate_matchup_value(cls, team_rating: Rating, team: str, opponent_rating: Rating, opponent: str) -> float:
        zscore = (team_rating.get_zscore(team) + opponent_rating.get_zscore(opponent)) / 2
        stdev = math.sqrt(pow(opponent_rating._stdevs.get(opponent), 2) + pow(team_rating._stdevs.get(team), 2))
        mean = (opponent_rating._averages.get(opponent) + team_rating._averages.get(team)) / 2
        return zscore * stdev + mean
