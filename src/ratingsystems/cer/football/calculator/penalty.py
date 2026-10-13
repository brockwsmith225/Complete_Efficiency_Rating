from .base import ExpectedPointsAddedCalculator


class PenaltyCalculator(ExpectedPointsAddedCalculator):

    def __call__(self, play):
        if not play.penalty:
            return

        try:
            # TODO: factor in down and distance (need to factor in loss of down? or assume nothing is a loss of down? all offensive penalties are?)
            if play.yards_gained >= play.yards_to_goal:
                # TODO: Data entry errors on PATs, I think all declined penalties that resulted in no next play
                return 0
            return self.expected_points(play.yards_to_goal - play.yards_gained) - self.expected_points(play.yards_to_goal)
        except Exception as e:
            print(play)
            raise e
