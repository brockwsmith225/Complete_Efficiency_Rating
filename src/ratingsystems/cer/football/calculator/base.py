from abc import ABC, abstractmethod

from ratingsystems.core.util import FilterList


class ExpectedPointsAddedCalculator(ABC):
    plays = None
    _expected_points = {}
    _first_down_odds = {}
    
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def prime(cls, plays: FilterList):
        if ExpectedPointsAddedCalculator.plays is not None and len(ExpectedPointsAddedCalculator.plays) == len(plays):
            return

        ExpectedPointsAddedCalculator.plays = plays

        drives = plays.filter(scrimmage=True).split("drive_id")
        drives = [sorted(drive, key=lambda p: p.play_number) for drive in drives.values()]

        ExpectedPointsAddedCalculator._expected_points = {}
        for yards_to_goal in range(1, 100):
            drives_here = [d for d in drives if any([p.yards_to_goal <= yards_to_goal for p in d])]
            scoring_drives_here = [d for d in drives_here if any([p.touchdown for p in d])]
            ExpectedPointsAddedCalculator._expected_points[yards_to_goal] = len(scoring_drives_here) / len(drives_here)

        min_value = min(ExpectedPointsAddedCalculator._expected_points.values())
        ExpectedPointsAddedCalculator._expected_points = {y: 7.0 * (value - min_value) / (1.0 - min_value) for y, value in ExpectedPointsAddedCalculator._expected_points.items()}
        ExpectedPointsAddedCalculator._expected_points[0] = 7.0

        sets_of_downs = []
        for drive in drives:
            for play in drive:
                if play.down == 1:
                    sets_of_downs.append([[], False, False])
                sets_of_downs[-1][0].append(play)
                if play.scoring:
                    sets_of_downs[-1][1] = True
            sets_of_downs[-1][2] = not sets_of_downs[-1][1]

        ExpectedPointsAddedCalculator._first_down_odds = {}
        for down in range(1, 5):
            ExpectedPointsAddedCalculator._first_down_odds[down] = {}
            for distance in range(1, 100):
                sets_of_downs_here = [d for d in sets_of_downs if any([p.distance <= distance and p.down == down for p in d[0]])]
                successful_sets_of_downs_here = [d for d in sets_of_downs_here if not d[2]]
                ExpectedPointsAddedCalculator._first_down_odds[down][distance] = len(successful_sets_of_downs_here) / len(sets_of_downs_here) if len(sets_of_downs_here) > 0 else 0
        
        base_value = ExpectedPointsAddedCalculator._first_down_odds[1][10]
        ExpectedPointsAddedCalculator._first_down_odds = {d: {y: (value - base_value) / (1.0 - base_value) for y, value in down.items()} for d, down in ExpectedPointsAddedCalculator._first_down_odds.items()}

    def expected_points(self, yards_to_goal: int) -> float:
        # TODO: protections for out of bounds?
        return ExpectedPointsAddedCalculator._expected_points[yards_to_goal]

    def first_down_odds(self, distance: int) -> float:
        # TODO: protections for out of bounds?
        return ExpectedPointsAddedCalculator._first_down_odds[distance]

    @abstractmethod
    def __call__(self, play):
        raise NotImplementedError()
