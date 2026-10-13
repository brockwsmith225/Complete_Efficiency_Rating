from numbers import Number
from typing import Any, Optional, Self


class FieldPosition:

    def __init__(self, down: int, distance: int, yards_to_goal: int):
        if down not in [1, 2, 3, 4]:
            raise IOError(f"Invalid down '{down}'")

        if distance <= 0 or distance >= 100:
            raise IOError(f"Invalid distance '{distance}'")

        if yards_to_goal <= 0 or yards_to_goal >= 100:
            raise IOError(f"Invalid yards to goal '{yards_to_goal}'")

        if distance > yards_to_goal:
            raise IOError(f"distance more than yards to goal '{distance} > {yards_to_goal}'")

        self.down = down
        self.distance = distance
        self.yards_to_goal = yards_to_goal

    def __str__(self) -> str:
        return f"{self.down}|{self.distance}|{self.yards_to_goal}"

    def __repr__(self) -> str:
        return f"FieldPosition({self})"

    def __hash__(self) -> int:
        # TODO: unit test to make sure this always stays unique
        return self.down * 10000 + self.distance * 100 + self.yards_to_goal

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


class Penalty:

    def __init__(self, down: int, distance: int):
        if down not in [0, 1]:
            raise IOError(f"Invalid down '{down}'")

        if distance <= -100 or distance >= 100:
            raise IOError(f"Invalid distance '{distance}'")

        self.down = down
        self.distance = distance

    def __str__(self) -> str:
        return f"{self.down}|{self.distance}"

    def __repr__(self) -> str:
        return f"Penalty({self})"

    def __hash__(self) -> int:
        if self.distance >= 0:
            return self.down * 100 + abs(self.distance)
        else:
            return -1 * (self.down * 100 + abs(self.distance))

    def __add__(self, other: Any) -> FieldPosition:
        if isinstance(other, FieldPosition):
            if self.distance > other.yards_to_goal / 2:
                distance = int(other.yards_to_goal / 2)
            elif self.distance < (other.yards_to_goal - 100) / 2:
                distance = int((other.yards_to_goal - 100) / 2)
            else:
                distance = self.distance
            if self.distance < other.distance:
                return FieldPosition(other.down + self.down, other.distance - distance, other.yards_to_goal - distance)
            else:
                return FieldPosition(1, min(10, other.yards_to_goal - distance), other.yards_to_goal - distance)
        return NotImplemented

    def __radd__(self, other: Any) -> FieldPosition:
        return self.__add__(other)
