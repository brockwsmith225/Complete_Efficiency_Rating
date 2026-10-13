from .base import ExpectedPointsAddedCalculator


class FieldGoalCalculator(ExpectedPointsAddedCalculator):

    def __call__(self, play):
        if not play.field_goal_attempt:
            return

        # TODO: is this a good way to calculate field goal value?
        #       maybe instead it should remove chance of TD and give 3/7?

        # Field Goal
        if play.field_goal_made:
            if play.yards_to_goal == 100:
                play.yards_to_goal = play.yards_gained
            # return 3 - self.expected_points(play.yards_to_goal)
            return (3/self.expected_points(0)) * (self.expected_points(0) - self.expected_points(play.yards_to_goal))

        if play.yards_to_goal == 100:
            # Data entry error
            return 0
        return -1 * self.expected_points(play.yards_to_goal)