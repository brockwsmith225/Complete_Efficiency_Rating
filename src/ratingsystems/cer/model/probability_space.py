from typing import Any, Callable, Self

from ratingsystems.cer.util.profile import profile


class ProbabilitySpace:

    def __init__(self, probabilities: dict[Any, float] = {}):
        # TODO: verify result is not different with deepcopy
        self._probabilities = probabilities.copy()

    def get(self, event) -> float:
        return self._probabilities.get(event, 0.0)

    def probability(self, predicate) -> float:
        if isinstance(predicate, Callable):
            return sum([probability for event, probability in self._probabilities.items() if predicate(event)])
        else:
            return self.get(predicate)

    def add(self, probability, event):
        if event not in self._probabilities:
            self._probabilities[event] = probability
            return
        self._probabilities[event] += probability

    def remove(self, event):
        if event in self._probabilities:
            del self._probabilities[event]

    def events(self):
        for event in self._probabilities.keys():
            yield event

    def normalize(self, value: float = 1.0):
        total_probability = sum(self._probabilities.values())
        self._probabilities = {event: probability / total_probability * value for event, probability in self._probabilities.items()}

    def __str__(self) -> str:
        return f"ProbabilitySpace({str(self._probabilities)})"

    def __repr__(self) -> str:
        return str(self)

    def __iter__(self):
        for event, probability in self._probabilities.items():
            yield probability, event

    def __len__(self):
        return len(self._probabilities)

    @profile
    def __add__(self, other: Any) -> Self:
        if isinstance(other, ProbabilitySpace):
            if len(self) > len(other):
                result = ProbabilitySpace(self._probabilities)
                for probability, event in other:
                    result.add(probability, event)
            else:
                result = ProbabilitySpace(other._probabilities)
                for probability, event in self:
                    result.add(probability, event)
        else:
            result = ProbabilitySpace()
            for probability, event in self:
                result.add(probability, event + other)
        return result

    @profile
    def __radd__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        if isinstance(other, ProbabilitySpace):
            for probability, event in self:
                result.add(probability, event)
            for probability, event in other:
                result.add(probability, event)
        else:
            for probability, event in self:
                result.add(probability, other + event)
        return result

    def __sub__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, event - other)
        return result

    def __rsub__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, other - event)
        return result

    def __mul__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, event * other)
        return result

    def __rmul__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, other * event)
        return result

    def __truediv__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, event / other)
        return result

    def __rtruediv__(self, other: Any) -> Self:
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability, other / event)
        return result

    def __pow__(self, other: Any) -> Self:
        """
        Multiply each probability in the ProbabilitySpace by other:
            ex. space ** 0.5 -> multiply each probability in `space` by 0.5
        """
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(probability * other, event)
        return result

    def __rpow__(self, other: Any) -> Self:
        """
        Multiply each probability in the ProbabilitySpace by other:
            ex. 0.5 ** space -> multiply each probability in `space` by 0.5
        """
        result = ProbabilitySpace()
        for probability, event in self:
            result.add(other * probability, event)
        return result


        from typing import Any, Self


# class ProbabilitySpace:

#     def __init__(self, probabilities: dict[Any, float] = {}):
#         self._probabilities = probabilities

#     def normalize(self, value: float = 1.0):
#         total_probability = sum(self._probabilities.values())
#         self._probabilities = {event: probability / total_probability * value for probability, event in self}

#     # @profile
#     def __add__(self, other: Any) -> Self:
#         if isinstance(other, ProbabilitySpace):
#             if len(self) > len(other):
#                 # TODO: verify result is not different with deepcopy
#                 result = ProbabilitySpace(self._probabilities.copy())
#                 for probability, event in other:
#                     result.add(probability, event)
#             else:
#                 result = ProbabilitySpace(other._probabilities.copy())
#                 for probability, event in self:
#                     result.add(probability, event)
#         else:
#             result = ProbabilitySpace()
#             for probability, event in self:
#                 result.add(probability, event + other)
#         return result

#     def __radd__(self, other: Any) -> Self:
#         return self.__add__(other)