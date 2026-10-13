from .base import ExpectedPointsAddedCalculator


class KickoffCalculator(ExpectedPointsAddedCalculator):

    def __init__(
        self,
        *args,
        touchback: int = 25,
        **kwargs,
    ):
        self.touchback = touchback
        super().__init__(*args, **kwargs)

    def __call__(self, play):
        try:
            # if play.turnover and play.down == 0:
            #     print(play)
            #     print()
            # if play.turnover and play.yards_to_goal == 100 and play.down == 0:
            #     # Fumble recovery on the kickoff
            #     return self.expected_points(100 - play.yards_gained)

            if not play.kickoff:
                return

            # TODO: handle successful onside kicks?
            if play.yards_gained == 0:
                # Touchback
                return 0

            if play.yards_gained < 0:
                play.yards_gained = 1

            # return self.expected_points(100 - self.touchback) - self.expected_points(100 - play.yards_gained)
            return self.expected_points(100 - play.yards_gained)
        except Exception as e:
            print(play)
            raise e
