from typing import Self

from cfbd.models.play import Play as _Play


class Play(_Play):
    # Scrimmage Plays
    _RUSHING_PLAY_TYPES = ["Rush", "Rushing Touchdown", "Fumble", "Fumble Recovery (Own)", "Fumble Recovery (Opponent)", "Fumble Return Touchdown", "Safety", "Two Point Rush"]
    _PASSING_PLAY_TYPES = ["Pass", "Pass Completion", "Pass Incompletion", "Sack", "Passing Touchdown", "Pass Reception", "Interception", "Pass Interception", "Pass Interception Return", "Interception Return Touchdown", "Two Point Pass"]
    _PASSING_COMPLETED_PLAY_TYPES = ["Pass", "Pass Completion", "Passing Touchdown", "Pass Reception", "Two Point Pass"]
    _SACK_PLAY_TYPES = ["Sack"]
    _TOUCHDOWN_PLAY_TYPES = ["Rushing Touchdown", "Passing Touchdown"]

    # Points After Touchdowns
    _EXTRA_POINT_MADE_PLAY_TYPES = ["Extra Point Good"]
    _EXTRA_POINT_ATTEMPT_PLAY_TYPES = ["Extra Point Good", "Extra Point Missed", "Blocked"]
    _TWO_POINT_PLAY_TYPES = ["Two Point Rush", "Two Point Pass", "2pt Conversion", "Defensive 2pt Conversion", "Offensive 1pt Safety"]
    _TWO_POINT_CONVERSION_TYPES = ["Two Point Rush", "Two Point Pass", "2pt Conversion", "Defensive 2pt Conversion", "Offensive 1pt Safety"]

    # Turnovers
    _FUMBLE_PLAY_TYPES = ["Fumble", "Fumble Recovery (Opponent)", "Fumble Return Touchdown"]
    _INTERCEPTION_PLAY_TYPES = ["Interception", "Pass Interception", "Pass Interception Return", "Interception Return Touchdown"]
    _DEFENSIVE_TOUCHDOWN_PLAY_TYPES = ["Fumble Return Touchdown", "Interception Return Touchdown"]
    _SAFETY_PLAY_TYPES = ["Safety"]

    # Field Goals
    _FIELD_GOAL_MADE_PLAY_TYPES = ["Field Goal Good"]
    _FIELD_GOAL_ATTEMPT_PLAY_TYPES = ["Field Goal Good", "Field Goal Missed", "Blocked Field Goal", "Missed Field Goal Return", "Missed Field Goal Return Touchdown"]
    _BLOCKED_FIELD_GOAL_PLAY_TYPES = ["Blocked Field Goal", "Blocked Field Goal Touchdown"]

    # Special Teams
    _KICKOFF_PLAY_TYPES = ["Kickoff", "Kickoff Return Touchdown", "Kickoff Return (Offense)", "Kickoff Return (Defense)"]
    _KICKOFF_RETURN_PLAY_TYPES = ["Kickoff Return Touchdown", "Kickoff Return (Offense)", "Kickoff Return (Defense)"]
    _PUNT_PLAY_TYPES = ["Punt", "Punt Return", "Punt Return Touchdown", "Blocked Punt", "Blocked Punt Touchdown"]
    _PUNT_RETURN_PLAY_TYPES = ["Punt Return", "Punt Return Touchdown"]
    _BLOCKED_PUNT_PLAY_TYPES = ["Blocked Punt", "Blocked Punt Touchdown"]
    _SPECIAL_TEAMS_TOUCHDOWN_PLAY_TYPES = ["Blocked Field Goal Touchdown", "Missed Field Goal Return Touchdown", "Kickoff Return Touchdown", "Punt Return Touchdown", "Blocked Punt Touchdown"]

    # Other
    _PENALTY_PLAY_TYPES = ["Penalty"]
    _TIMEOUT_PLAY_TYPES = ["Timeout"]
    _ADMIN_PLAY_TYPES = ["Penalty", "Timeout", "Start of Period", "End Period", "End of Half", "End of Regulation", "End of Game"]
    _OTHER_PLAY_TYPES = ["placeholder", "Uncategorized"]

    __KNOWN_PLAY_TYPES = set(
        _RUSHING_PLAY_TYPES +
        _PASSING_PLAY_TYPES +
        _PASSING_COMPLETED_PLAY_TYPES +
        _SACK_PLAY_TYPES +
        _TOUCHDOWN_PLAY_TYPES +
        _EXTRA_POINT_MADE_PLAY_TYPES +
        _EXTRA_POINT_ATTEMPT_PLAY_TYPES +
        _TWO_POINT_PLAY_TYPES +
        _FUMBLE_PLAY_TYPES +
        _INTERCEPTION_PLAY_TYPES +
        _DEFENSIVE_TOUCHDOWN_PLAY_TYPES +
        _SAFETY_PLAY_TYPES +
        _FIELD_GOAL_MADE_PLAY_TYPES +
        _FIELD_GOAL_ATTEMPT_PLAY_TYPES +
        _BLOCKED_FIELD_GOAL_PLAY_TYPES +
        _KICKOFF_PLAY_TYPES +
        _KICKOFF_RETURN_PLAY_TYPES +
        _PUNT_PLAY_TYPES +
        _PUNT_RETURN_PLAY_TYPES +
        _BLOCKED_PUNT_PLAY_TYPES +
        _SPECIAL_TEAMS_TOUCHDOWN_PLAY_TYPES +
        _PENALTY_PLAY_TYPES +
        _TIMEOUT_PLAY_TYPES +
        _ADMIN_PLAY_TYPES +
        _OTHER_PLAY_TYPES
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: handle Uncategorized

        if self.play_type not in self.__KNOWN_PLAY_TYPES:
            raise TypeError(f"Unknown play type '{self.play_type}'")

    @classmethod
    def from_dict(cls, kwargs: dict) -> Self:
        return cls(**kwargs)

    @property
    def rushing(self):
        return self.play_type in self._RUSHING_PLAY_TYPES

    @property
    def passing(self):
        return self.play_type in self._PASSING_PLAY_TYPES

    @property
    def passing_completed(self):
        return self.play_type in self._PASSING_COMPLETED_PLAY_TYPES

    @property
    def sack(self):
        return self.play_type in self._SACK_PLAY_TYPES

    @property
    def scrimmage(self):
        return self.rushing or self.passing

    @property
    def touchdown(self):
        return self.play_type in self._TOUCHDOWN_PLAY_TYPES

    @property
    def pat(self):
        return self.extra_point_attempt or self.two_point_attempt

    @property
    def extra_point_made(self):
        return self.play_type in self._EXTRA_POINT_MADE_PLAY_TYPES

    @property
    def extra_point_attempt(self):
        return self.play_type in self._EXTRA_POINT_ATTEMPT_PLAY_TYPES

    @property
    def two_point_attempt(self):
        return self.play_type in self._TWO_POINT_PLAY_TYPES

    @property
    def two_point_conversion(self):
        return self.two_point_attempt and self.scoring

    @property
    def field_goal_made(self):
        return self.play_type in self._FIELD_GOAL_MADE_PLAY_TYPES

    @property
    def field_goal_attempt(self):
        return self.play_type in self._FIELD_GOAL_ATTEMPT_PLAY_TYPES

    @property
    def kickoff(self):
        return self.play_type in self._KICKOFF_PLAY_TYPES

    @property
    def kickoff_return(self):
        return self.play_type in self._KICKOFF_RETURN_PLAY_TYPES

    @property
    def punt(self):
        return self.play_type in self._PUNT_PLAY_TYPES

    @property
    def punt_return(self):
        return self.play_type in self._PUNT_RETURN_PLAY_TYPES

    @property
    def punt_block(self):
        return self.play_type in self._BLOCKED_PUNT_PLAY_TYPES

    @property
    def special(self):
        return self.field_goal_attempt or self.kickoff or self.punt

    @property
    def fumble(self):
        return self.play_type in self._FUMBLE_PLAY_TYPES

    @property
    def interception(self):
        return self.play_type in self._INTERCEPTION_PLAY_TYPES

    @property
    def defensive_touchdown(self):
        return self.play_type in self._DEFENSIVE_TOUCHDOWN_PLAY_TYPES

    @property
    def safety(self):
        return self.play_type in self._SAFETY_PLAY_TYPES

    @property
    def turnover(self):
        return self.fumble or self.interception or self.safety

    @property
    def penalty(self):
        return self.play_type in self._PENALTY_PLAY_TYPES

    @property
    def timeout(self):
        return self.play_type in self._TIMEOUT_PLAY_TYPES

    @property
    def admin(self):
        return self.play_type in self._ADMIN_PLAY_TYPES

    @property
    def other(self):
        return self.play_type in self._OTHER_PLAY_TYPES