from numbers import Number
from typing import Any, Optional, Self


class FieldPosition:

    def __init__(self, down: int, distance: int, yards_to_goal: int):
        self.down = down
        self.distance = distance
        self.yards_to_goal = yards_to_goal

    def __str__(self):
        return f"{self.down}-{self.distance}-{self.yards_to_goal}"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, FieldPosition):
            return self.down == other.down and self.distance == other.distance and self.yards_to_goal == other.yards_to_goal
        return NotImplemented

    def __add__(self, yards_gained: Any) -> Optional[Self]:
        if isinstance(yards_gained, Number):
            if yards_gained < self.distance:
                if self.down == 4:
                    return None
                return FieldPosition(self.down + 1, self.distance - yards_gained, self.yards_to_goal - yards_gained)
            else:
                return FieldPosition(1, min(10, self.yards_to_goal - yards_gained), self.yards_to_goal - yards_gained)
        return NotImplemented

    def __radd__(self, yards_gained: Any) -> Optional[Self]:
        return self.__add__(yards_gained)

    def __sub__(self, yards_lost: Any) -> Self:
        if isinstance(yards_lost, Number):
            return FieldPosition(self.down + 1, self.distance + yards_lost, self.yards_to_goal + yards_lost)
        return NotImplemented

    @classmethod
    def all(cls) -> Self:
        for down in range(1, 5):
            for yards_to_goal in range(1, 100):
                for distance in range(1, yards_to_goal):
                    yield cls(down, distance, yards_to_goal)
