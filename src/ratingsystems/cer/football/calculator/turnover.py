from .base import ExpectedPointsAddedCalculator


class TurnoverCalculator(ExpectedPointsAddedCalculator):

    def __call__(self, play):
        if not play.turnover:
            return

        try:
            if play.yards_to_goal == 100:
                if play.scoring:
                    # Defensive score
                    # TODO: handle safety and other scores
                    return -self.expected_points(min(100 - play.yards_gained, 99))
                else:
                    # Fumble on kickoff
                    return self.expected_points(100 - play.yards_gained)
            if play.yards_to_goal == 0:
                # TODO: data entry error
                return

            yardline = 100 - play.yards_to_goal
            new_yards_to_goal = min(yardline + play.yards_gained, 99)

            if play.scoring:
                return self.expected_points(0) - self.expected_points(yardline)

            return self.expected_points(new_yards_to_goal)

        except Exception as e:
            print(play)
            raise e