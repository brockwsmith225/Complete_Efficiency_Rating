import math
from abc import ABC, abstractmethod
from scipy.stats import norm, skewnorm
from typing import Self


class Distribution(ABC):

    def __init__(self):
        pass

    @classmethod
    @abstractmethod
    def fit(cls, data: list[float]) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def pdf(self, value: float) -> float:
        raise NotImplementedError()

    @abstractmethod
    def sampling(self, sampling_size: int = 1000) -> list[float]:
        raise NotImplementedError()


class NormalDistribution(Distribution):

    def __init__(self, mean: float, variance: float):
        super().__init__()
        self.mean = mean
        self.variance = abs(variance)

    @classmethod
    def fit(cls, data) -> Self:
        result = norm.fit(data)
        mean = result[-2]
        variance = pow(result[-1], 2)
        return cls(
            mean=mean,
            variance=variance,
        )

    def zscore(self, value: float) -> float:
        if self.variance == 0:
            return 0.0
        return (value - self.mean) / math.sqrt(self.variance)

    def value(self, zscore: float) -> float:
        return zscore * math.sqrt(self.variance) + self.mean

    def pdf(self, value: float) -> float:
        return float(norm.pdf(value, loc=self.mean, scale=math.sqrt(self.variance)))

    def cdf(self, value: float) -> float:
        return float(norm.cdf(value, loc=self.mean, scale=math.sqrt(self.variance)))

    def sampling(self, sampling_size: int = 1000) -> list[float]:
        return [float(x) for x in norm.rvs(loc=self.mean, scale=math.sqrt(self.variance), size=sampling_size)]

    def random(self) -> float:
        return self.sampling(1)[0]

    def __str__(self):
        return f"({self.mean}, {self.variance})"

    def __repr__(self):
        return str(self)

    # TODO: math functions should follow real rules for Normal Distributions

    def __add__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean + other.mean, self.variance + other.variance)
        else:
            return NormalDistribution(self.mean + other, self.variance)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean - other.mean, self.variance - other.variance)
        else:
            return NormalDistribution(self.mean - other, self.variance)

    def __rsub__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean - self.mean, other.variance - self.variance)
        else:
            return NormalDistribution(other - self.mean, self.variance)

    def __mul__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean * other.mean, self.variance * other.variance)
        else:
            return NormalDistribution(self.mean * other, self.variance * abs(other))

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean / other.mean, self.variance / abs(other.variance))
        else:
            return NormalDistribution(self.mean / other, self.variance / abs(other))

    def __rtruediv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean / self.mean, abs(other.variance) / self.variance)
        else:
            return NormalDistribution(other / self.mean, abs(other) / self.variance)

    def __floordiv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.mean // other.mean, self.variance // abs(other.variance))
        else:
            return NormalDistribution(self.mean // other, self.variance // abs(other))

    def __rfloordiv__(self, other):
        if isinstance(other, NormalDistribution):
            return NormalDistribution(other.mean // self.mean, abs(other.variance) // self.variance)
        else:
            return NormalDistribution(other // self.mean, abs(other) // self.variance)

    def __pow__(self, other):
        return NormalDistribution(math.pow(self.mean, other), math.pow(self.variance, other))

    def __eq__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean == other.mean and self.variance == other.variance
        else:
            return False

    def __le__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean <= other.mean
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean < other.mean
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean >= other.mean
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, NormalDistribution):
            return self.mean > other.mean
        else:
            return False

    def __hash__(self):
        return hash((self.mean, self.variance))


class SkewNormalDistribution(Distribution):

    def __init__(self, location: float, scale: float, shape: float):
        super().__init__()
        self.location = location
        self.scale = scale
        self.shape = shape

    @classmethod
    def fit(cls, data: list[float]) -> Self:
        shape, location, scale = skewnorm.fit(data)
        return cls(
            location=location,
            scale=scale,
            shape=shape,
        )

    def pdf(self, value: float) -> float:
        return float(skewnorm.pdf(value, a=self.shape, loc=self.location, scale=self.scale))

    def sampling(self, sampling_size: int = 1000) -> list[float]:
        return [float(x) for x in skewnorm.rvs(a=self.shape, loc=self.location, scale=self.scale, size=sampling_size)]

    def random(self) -> float:
        return self.sampling(1)[0]

    def __add__(self, other):
        if isinstance(other, Distribution):
            raise NotImplemented
        else:
            return SkewNormalDistribution(self.location + other, self.scale, self.shape)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Distribution):
            raise NotImplemented
        else:
            return SkewNormalDistribution(self.location - other, self.scale, self.shape)

    def __rsub__(self, other):
        if isinstance(other, Distribution):
            raise NotImplemented
        else:
            return SkewNormalDistribution(other - self.location, self.scale, self.shape)

    def __mul__(self, other):
        if isinstance(other, Distribution):
            raise NotImplemented
        else:
            return SkewNormalDistribution(self.location * other, self.scale * abs(other), self.shape * 1 if other >= 0 else -1)

    def __rmul__(self, other):
        return self.__mul__(other)
