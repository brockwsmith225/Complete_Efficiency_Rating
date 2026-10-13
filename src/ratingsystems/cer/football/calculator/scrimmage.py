from .base import ExpectedPointsAddedCalculator


class ScrimmageCalculator(ExpectedPointsAddedCalculator):

    def __init__(
        self,
        *args,
        rushing: bool = False,
        passing: bool = False,
        **kwargs,
    ):
        if not rushing and not passing:
            self.rushing = True
            self.passing = True
        else:
            self.rushing = rushing
            self.passing = passing

        super().__init__(*args, **kwargs)

    def __call__(self, play):
        try:
            if play.admin or play.other or play.kickoff or play.punt or play.penalty or play.field_goal_attempt:
                return

            if not self.rushing and play.rushing:
                return

            if not self.passing and play.passing:
                return

            # if play.punt:
            #     return -self.expected_points(play.yards_to_goal)

            if play.turnover:
                # Lost points for losing the ball to a turnover
                if play.yards_to_goal == 100:
                    # Data entry errors
                    return
                    # if play.scoring:
                    #     # Defensive score
                    #     # TODO: handle safety and other scores
                    #     return -self.expected_points(min(100 - play.yards_gained, 99))
                    # else:
                    #     # Fumble on kickoff
                    #     return
                    #     # return self.expected_points(100 - play.yards_gained)

                return -self.expected_points(play.yards_to_goal)

            if play.touchdown:
                # Touchdown
                if play.yards_gained == 0:
                    play.yards_gained = 1
                play.yards_to_goal = play.yards_gained
                return self.expected_points(0) - self.expected_points(play.yards_to_goal)

            if play.pat:
                # TODO: handle PAT: XP, 2p, defensive 2p, and offensive 1p safety
                return 0

            if play.down == 0:
                # Two Point Attempt
                if play.scoring:
                    # TODO: change to 1
                    return (2/self.expected_points(0)) * (self.expected_points(0) - self.expected_points(play.yards_to_goal))
                return self.expected_points(play.yards_to_goal - play.yards_gained) - self.expected_points(play.yards_to_goal)

            if play.yards_gained > play.yards_to_goal:
                # TODO: what to do with these plays? data entry errors
                return 0

            # Value of getting a first down
            first_and_ten_yardline = min(play.yards_to_goal - play.distance + 10, 99)
            first_down_yardline = play.yards_to_goal - play.distance
            if first_down_yardline <= 0:
                # Data entry error
                return 0
            first_down_epa = self.expected_points(first_down_yardline) - self.expected_points(first_and_ten_yardline)

            # Success rate within this set of downs
            if play.yards_gained >= play.distance:
                # First down
                first_down_odds = 1 - self.first_down_odds(play.down)[play.distance]
            else:
                first_down_odds = self.first_down_odds(play.down + 1)[play.distance - play.yards_gained] - self.first_down_odds(play.down)[play.distance]

            # Success rate of extra yards beyond first down
            extra_yards = max(play.yards_gained - play.distance, 0)
            extra_yards_epa = self.expected_points(first_down_yardline - extra_yards) - self.expected_points(first_down_yardline)

            success_rate = first_down_odds * first_down_epa + extra_yards_epa

            return success_rate

        except Exception as e:
            print(play)
            raise e
