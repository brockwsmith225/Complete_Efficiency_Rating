import math
import scipy.stats as st

from ratingsystems import Prediction, Predictor, Rating


class FootballPredictor(Predictor):

    def __init__(self, rating: Rating):
        super().__init__(rating)

    def predict(self, team: str, opponent: str) -> Prediction:
        rushing = self.rating.offense.efficiency.rushing._predictor(team, opponent)
        passing = self.rating.offense.efficiency.passing._predictor(team, opponent)
        field_goals = self.rating.offense._field_goals._predictor(team, opponent)
        turnovers = self.rating.offense._turnovers._predictor(opponent, team)
        kickoffs = self.rating.offense._kickoffs._predictor(opponent, team)
        punts = self.rating.offense._punts._predictor(opponent, team)
        print(f"rushing={rushing}")
        print(f"passing={passing}")
        print(f"field_goals={field_goals}")
        print(f"turnovers={turnovers}")
        print(f"kickoffs={kickoffs}")
        print(f"punts={punts}")
        print("="*100)
        # TODO: multiply by tempo of each team?
        team_score = self.rating._avg_num_drives * (rushing + passing + field_goals + turnovers + kickoffs + punts)

        rushing = self.rating.offense.efficiency.rushing._predictor(opponent, team)
        passing = self.rating.offense.efficiency.passing._predictor(opponent, team)
        field_goals = self.rating.offense._field_goals._predictor(opponent, team)
        turnovers = self.rating.offense._turnovers._predictor(team, opponent)
        kickoffs = self.rating.offense._kickoffs._predictor(team, opponent)
        punts = self.rating.offense._punts._predictor(team, opponent)
        print(f"rushing={rushing}")
        print(f"passing={passing}")
        print(f"field_goals={field_goals}")
        print(f"turnovers={turnovers}")
        print(f"kickoffs={kickoffs}")
        print(f"punts={punts}")
        print("="*100)
        # TODO: multiply by tempo of each team?
        opponent_score = self.rating._avg_num_drives * (rushing + passing + field_goals + turnovers + kickoffs + punts)

        return Prediction(
            team,
            opponent,
            line=team_score - opponent_score,
            odds=st.norm.cdf((team_score - opponent_score) / self.rating.confidence_interval),
            team_score=team_score,
            opponent_score=opponent_score,
        )
