from statistics import fmean

from ratingsystems.core.util import FilterList

from .base import ExpectedPointsAddedCalculator


class PuntCalculator(ExpectedPointsAddedCalculator):

    def __init__(
        self,
        *args,
        touchback: int = 20,
        **kwargs,
    ):
        self.touchback = touchback
        self.average_punt = None
        super().__init__(*args, **kwargs)

    def prime(self, plays: FilterList):
        self.average_punt = round(fmean([p.yards_gained for p in plays.filter(punt=True)]))
        super().prime(plays)

    def __call__(self, play):
        if not play.punt:
            return

        try:
            line_of_scrimmage = 100 - play.yards_to_goal
            result = min(line_of_scrimmage + play.yards_gained, 99)
            expected_punt = min(line_of_scrimmage + self.average_punt, 100 - self.touchback)

            if result > 100:
                # TODO: what to do with these plays? data entry errors
                return 0

            # return self.expected_points(expected_punt) - self.expected_points(result)
            return self.expected_points(result)
        except Exception as e:
            print(play)
            raise e
