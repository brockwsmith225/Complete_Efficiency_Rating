import math
import multiprocessing
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import partial
from statistics import fmean, stdev
from typing import Callable

from ratingsystems import Play
from ratingsystems.core.util import FilterList

from ratingsystems.data.model import FootballPlay as Play

from ratingsystems.cer.model import FieldPosition, ProbabilitySpace, Possession
from ratingsystems.cer.util.profile import profile
from ratingsystems.cer.util.adjusted import AdjustedStat, AdjustedDistribution
from ratingsystems.cer.util.statistics import NormalDistribution

from .play.penalty import PenaltyEngine
from .play.playcall import Playcall, PlaycallEngine
from .play.scoring import FieldGoalEngine, TouchdownEngine
from .play.turnover import TurnoverEngine
from .play.yards import PassYardsEngine, RushYardsEngine


class DriveEngine():

    def __init__(
        self,
        plays: FilterList[Play],
        precision: float = 0.000001,
        max_yards_lost: int = -5,
        max_yards_gained: int = 99,
        validate: bool = True,
        separate_redzone: bool = True,
    ):
        print("Creating Drive Engine ...")

        self.plays = plays
        self.precision = precision
        self.max_yards_lost = max_yards_lost
        self.max_yards_gained = max_yards_gained
        self.validate = validate
        self.separate_redzone = separate_redzone

        self.outer_count = 0
        self.outer_time = 0
        self.inner_count = 0
        self.inner_time = 0

        # games = plays.split("game_id")
        # teams = {}
        # num_drives = []
        # team_drives = {}
        # points = []
        # for game in games.values():
        #     num_drives.append(len(game.split("drive_number")))
        #     teams = game.filter(scrimmage=True).split("offense")
        #     for t, team in teams.items():
        #         if t not in team_drives:
        #             team_drives[t] = []
        #         team_drives[t].append(len(team.split("drive_number")))
        #     points.append(7 * len(game.filter(touchdown=True)) + 3 * len(game.filter(field_goal_made=True))) #+ 2 * len(game.filter(two_point_conversion=True)) + 1 * len(game.filter(extra_point_made=True)))

        # teams = plays.split("offense")
        # self.avg_num_drives = fmean(num_drives) / 2
        # print(f"drives={self.avg_num_drives}")
        # stats = [sum(team_drives[t]) / len(team.split("game_id")) for t, team in teams.items()]
        # print(f"drives={fmean(stats)} ({stdev(stats)})")
        # points = [p / 2 for p in points]
        # self.avg_points = fmean(points)
        # print(f"points={self.avg_points} ({stdev(points)})")
        # stats = [len(team) / sum(team_drives[t]) for t, team in teams.items()]
        # print(f"plays={fmean(stats)} ({stdev(stats)})")
        # stats = [len(team.filter(rushing=True)) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f"rush_pct={fmean(stats)} ({stdev(stats)})")
        # stats = [len(team.filter(passing=True)) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f"pass_pct={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(scrimmage=True) if p.yards_gained >= 10]) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f">10={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(scrimmage=True) if p.yards_gained >= 20]) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f">20={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(scrimmage=True) if p.yards_gained >= 30]) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f">30={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(scrimmage=True) if p.yards_gained >= 40]) / len(team.filter(scrimmage=True)) for team in teams.values()]
        # print(f">40={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(down=3) if p.yards_gained >= p.distance]) / len(team.filter(down=3)) for team in teams.values()]
        # print(f"3rd down={fmean(stats)} ({stdev(stats)})")
        # stats = [len([p for p in team.filter(down=4) if p.yards_gained >= p.distance]) / len(team.filter(down=4)) for team in teams.values()]
        # print(f"4th down={fmean(stats)} ({stdev(stats)})")
        # stats = [len(team.filter(touchdown=True)) / sum(team_drives[t]) for t, team in teams.items()]
        # print(f"touchdown={fmean(stats)} ({stdev(stats)})")
        # stats = [len(team.filter(field_goal_made=True)) / sum(team_drives[t]) for t, team in teams.items()]
        # print(f"field goal={fmean(stats)} ({stdev(stats)})")

        admin_plays = plays.filter(admin=True)
        plays = plays.filter(admin=False, other=False)

        self.playcall_engine = PlaycallEngine(plays.filter(penalty=False))

        self.penalty_engine = PenaltyEngine(plays)

        plays = plays.filter(penalty=False)

        self.field_goal_engine = FieldGoalEngine(plays)

        plays = plays.filter(scrimmage=True)

        self.fumble_engine = TurnoverEngine(plays.filter(rushing=True))
        self.interception_engine = TurnoverEngine(plays.filter(passing=True))

        self.rush_touchdown_engine = TouchdownEngine(plays.filter(rushing=True, yards_to_goal=lambda y: y <= 20))
        self.pass_touchdown_engine = TouchdownEngine(plays.filter(passing=True, yards_to_goal=lambda y: y <= 20))

        # TODO: don't filter out scoring?
        plays = plays.filter(turnover=False)

        self.rush_yards_engine = RushYardsEngine(
            plays,
            max_yards_lost=self.max_yards_lost,
            max_yards_gained=self.max_yards_gained,
            separate_redzone=self.separate_redzone,
            probability_cutoff=self.precision,
            sampling_size=10000,
        )
        self.pass_yards_engine = PassYardsEngine(
            plays,
            max_yards_lost=self.max_yards_lost,
            max_yards_gained=self.max_yards_gained,
            separate_redzone=self.separate_redzone,
            probability_cutoff=self.precision,
            sampling_size=10000,
        )
        # TODO: penalty engine
        # TODO: defensive scoring?

        multiprocessing.set_start_method("spawn")

        print("Created Drive Engine...")

        profile.reset()

    @profile
    def run(self, possession: Possession, collect_stats: bool = True):
        # print("Running Drive Engine: ...")
        # starttime = time.time()

        # initialize drive details
        # TODO: replace with field position engine
        field_positions = ProbabilitySpace({FieldPosition(1, 10, 75): 1.0})
        plays = {}
        drive_end_pct = 0.0
        expected_points = 0.0
        num_plays = 0.0
        num_rush_plays = 0.0
        num_pass_plays = 0.0
        # completions = 0.0
        explosive_plays_10 = 0.0
        explosive_plays_20 = 0.0
        explosive_plays_30 = 0.0
        explosive_plays_40 = 0.0
        third_down_conversions = 0.0
        third_down_attempts = 0.0
        fourth_down_conversions = 0.0
        fourth_down_attempts = 0.0
        touchdown_pct = 0.0
        field_goal_pct = 0.0

        self.rush_yards_engine.prime(possession)
        self.pass_yards_engine.prime(possession)

        # with multiprocessing.Pool(16) as pool:
        outer_starttime = time.time()
        while True:
            if len(field_positions) == 0:
                break
                raise Exception(f"out of plays, drive end pct: {drive_end_pct}")

            results = ProbabilitySpace()

            # plays that we have not already simulated
            new_field_positions = [
                field_position
                for play_probability, field_position in field_positions
                if field_position not in plays
            ]

            # simulate a play
            for field_position in new_field_positions:
                plays[field_position] = self.calculate_play(field_position, possession.offense, possession.defense)
            # for play in pool.map(partial(self.calculate_play, offense=possession.offense, defense=possession.defense), new_field_positions):
            #     plays[FieldPosition(play.down, play.distance, play.yards_to_goal)] = play

            inner_starttime = time.time()
            for play_probability, field_position in field_positions:
                play = plays[field_position]

                drive_end_pct += play.drive_end_pct * play_probability
                expected_points += play.expected_points * play_probability
                for probability, fp in play.field_positions:
                    results.add(probability * play_probability, fp)

                # Other stats
                if collect_stats:
                    if play.scrimmage_pct > 0:
                        num_plays += play_probability * play.scrimmage_pct
                        num_rush_plays += play_probability * play.scrimmage_pct * play.rush_pct
                        num_pass_plays += play_probability * play.scrimmage_pct * play.pass_pct
                        # completions += play_probability * (play. * play.pass_pct / (play.rush_pct + play.pass_pct))
                        # TODO: * (1 - play.end_pct)
                        # explosive_plays_10 += play_probability * play.scrimmage_pct * ((1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= 10) + play.touchdown_pct if play.yards_to_goal >= 10 else 0.0)
                        # explosive_plays_20 += play_probability * play.scrimmage_pct * ((1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= 20) + play.touchdown_pct if play.yards_to_goal >= 20 else 0.0)
                        # explosive_plays_30 += play_probability * play.scrimmage_pct * ((1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= 30) + play.touchdown_pct if play.yards_to_goal >= 30 else 0.0)
                        # explosive_plays_40 += play_probability * play.scrimmage_pct * ((1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= 40) + play.touchdown_pct if play.yards_to_goal >= 40 else 0.0)
                        if play.down == 3:
                            # third_down_conversions += play_probability * (play.touchdown_pct + (1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= play.distance))
                            third_down_attempts += play_probability
                        if play.down == 4:
                            # fourth_down_conversions += play_probability * play.scrimmage_pct * (play.touchdown_pct + (1 - play.drive_end_pct) * play.yards_gained.probability(lambda x: x >= play.distance))
                            fourth_down_attempts += play_probability * play.scrimmage_pct
                        touchdown_pct += play_probability * play.scrimmage_pct * play.touchdown_pct
                    field_goal_pct += play_probability * play.fga_pct * play.fgm_pct
                
                self.inner_count += 1

            self.inner_time += time.time() - inner_starttime

            # account for turnover on downs
            drive_end_pct += results.get(None)
            results.remove(None)

            field_positions = results
            field_positions._probabilities = {
                event: probability
                for probability, event in field_positions
                if probability > self.precision
            }

            self.outer_count += 1

        self.outer_time += time.time() - outer_starttime

        possession.end_pct = drive_end_pct
        possession.expected_points = expected_points / drive_end_pct

        # Other stats
        if collect_stats:
            possession.num_plays = num_plays / drive_end_pct
            possession.rush_pct = num_rush_plays / num_plays
            possession.pass_pct = num_pass_plays / num_plays
            possession.explosive_play_10_pct = explosive_plays_10 / num_plays
            possession.explosive_play_20_pct = explosive_plays_20 / num_plays
            possession.explosive_play_30_pct = explosive_plays_30 / num_plays
            possession.explosive_play_40_pct = explosive_plays_40 / num_plays
            possession.third_down_conversion_pct = third_down_conversions / third_down_attempts
            possession.fourth_down_conversion_pct = fourth_down_conversions / fourth_down_attempts
            possession.touchdown_pct = touchdown_pct / drive_end_pct
            possession.field_goal_pct = field_goal_pct / drive_end_pct
        else: 
            possession.num_plays = 0
            possession.rush_pct = 0
            possession.pass_pct = 0
            possession.explosive_play_10_pct = 0
            possession.explosive_play_20_pct = 0
            possession.explosive_play_30_pct = 0
            possession.explosive_play_40_pct = 0
            possession.third_down_conversion_pct = 0
            possession.fourth_down_conversion_pct = 0
            possession.touchdown_pct = 0
            possession.field_goal_pct = 0

        return possession

        # print(f"Ran Drive Engine after {time.time() - starttime} seconds")

    def prime(self, possession: Possession):
        self.rush_yards_engine.prime(possession)
        self.pass_yards_engine.prime(possession)

    def simulate(self, possession: Possession) -> int:
        field_position = FieldPosition(1, 10, 75)

        while True:
            if field_position is None:
                return 0

            play = Possession(offense=possession.offense, defense=possession.defense)

            # Set play position
            play.down = field_position.down
            play.distance = field_position.distance
            play.yards_to_goal = field_position.yards_to_goal

            playcall = self.playcall_engine.simulate(play)

            if playcall == "punt":
                return 0

            elif playcall == "fga":
                if self.field_goal_engine.simulate(play):
                    return 3
                else:
                    return 0

            elif playcall == "rush":
                if self.fumble_engine.simulate(play):
                    return 0

                yards = self.rush_yards_engine.simulate(play)
                if yards >= field_position.yards_to_goal:
                    return 7

                field_position = field_position + yards
                continue

            elif playcall == "pass":
                if self.interception_engine.simulate(play):
                    return 0

                yards = self.pass_yards_engine.simulate(play)
                if yards >= field_position.yards_to_goal:
                    return 7

                field_position = field_position + yards
                continue

            else:
                raise Exception(f"Unrecognized playcall '{playcall}'")

    @profile
    def calculate_play(self, field_position: FieldPosition, offense, defense) -> PlayResult:
        play = Possession(offense=offense, defense=defense)

        # Set play position
        play.down = field_position.down
        play.distance = field_position.distance
        play.yards_to_goal = field_position.yards_to_goal

        # Playcall for this play (run/pass/punt/fga)
        playcall = self.playcall_engine.run(play)

        if self.validate:
            assert_sum(1, playcall.scrimmage_pct, playcall.fga_pct, playcall.punt_pct)
            assert_sum(1, playcall.rush_pct, playcall.pass_pct)

        # Chance for a penalty to occur on this play
        penalty_yards = self.penalty_engine.run(play)
        penalty_pct = penalty_yards.total()

        if self.validate:
            assert penalty_pct < 0.2, penalty_pct

        # Chance to score a field goal on a field goal attempt
        if playcall.fga_pct > 0:
            fgm_pct = self.field_goal_engine.run(play)
            # assert fgm_pct > 0.3, f"{fgm_pct} {field_position}"
            # TODO: what is a valid expectation for fgm_pct?
        else:
            fgm_pct = 0

        # Chance of a turnover on a scrimmage play
        fumble_pct = self.fumble_engine.run(play)
        interception_pct = self.interception_engine.run(play)
        turnover_pct = ((fumble_pct * playcall.rush_pct) + (interception_pct * playcall.pass_pct))

        if self.validate:
            assert turnover_pct < 0.1, turnover_pct

        # Yards gained on a rushing play
        rush_yards = self.rush_yards_engine.run(play)

        # Yards gained on a passing play
        pass_yards = self.pass_yards_engine.run(play)

        if self.validate:
            assert_sum(1, rush_yards.total())
            assert_sum(1, pass_yards.total())

        # Yards gained on a scrimmage play
        yards_gained = (rush_yards ** playcall.rush_pct) + (pass_yards ** playcall.pass_pct)

        if self.validate:
            assert_sum(1, yards_gained.total())

        if self.separate_redzone and field_position.yards_to_goal <= 20:
            rush_touchdown_pct = self.rush_touchdown_engine.run(play)
            pass_touchdown_pct = self.pass_touchdown_engine.run(play)

            touchdown_pct = ((rush_touchdown_pct * playcall.rush_pct) + (pass_touchdown_pct * playcall.pass_pct))
        else:
            touchdown_pct = yards_gained.probability(lambda y: y >= field_position.yards_to_goal)
        # TODO: handle PAT

        # Remove any yards gained that would result in a touchdown
        for y in range(field_position.yards_to_goal, 100):
            yards_gained.remove(y)
        yards_gained.normalize()

        if self.validate:
            assert_sum(1, yards_gained.total())

        # Chance the drive ends on this play
        drive_end_pct = playcall.punt_pct + playcall.fga_pct + playcall.scrimmage_pct * (1 - penalty_pct) * (turnover_pct + touchdown_pct)

        # Expected points from this play
        expected_points = (7 * playcall.scrimmage_pct * (1 - penalty_pct) * touchdown_pct) + (3 * playcall.fga_pct * fgm_pct)

        # Probabilty space of possible field positions resulting from this play
        field_positions = field_position + yards_gained ** (playcall.scrimmage_pct * (1 - penalty_pct) * (1 - turnover_pct - touchdown_pct))

        # Add in possible penalty yards
        for probability, penalty in penalty_yards:
            field_positions.add(probability * playcall.scrimmage_pct, field_position + penalty)

        if self.validate:
            assert_sum(1, drive_end_pct, field_positions.total())

        # if field_position.down == 4:
        #     print(field_position)
        #     print(f"punt={playcall.punt_pct}")
        #     print(f"fga={playcall.fga_pct}")
        #     print(f"scrimmage={playcall.scrimmage_pct}")

        return PlayResult(
            drive_end_pct=drive_end_pct,
            expected_points=expected_points,
            field_positions=field_positions,
            scrimmage_pct=playcall.scrimmage_pct,
            rush_pct=playcall.rush_pct,
            pass_pct=playcall.pass_pct,
            fga_pct=playcall.fga_pct,
            punt_pct=playcall.punt_pct,
            fgm_pct=fgm_pct,
            fumble_pct=fumble_pct,
            interception_pct=interception_pct,
            turnover_pct=turnover_pct,
            # rush_touchdown_pct=rush_touchdown_pct,
            # pass_touchdown_pct=pass_touchdown_pct,
            touchdown_pct=touchdown_pct,
            yards_gained=yards_gained,
            down=field_position.down,
            distance=field_position.distance,
            yards_to_goal=field_position.yards_to_goal,
        )


@dataclass
class PlayResult:
    drive_end_pct: float
    expected_points: float
    field_positions: ProbabilitySpace

    scrimmage_pct: float
    rush_pct: float
    pass_pct: float
    fga_pct: float
    punt_pct: float
    fgm_pct: float
    fumble_pct: float
    interception_pct: float
    turnover_pct: float
    # rush_touchdown_pct: float
    # pass_touchdown_pct: float
    touchdown_pct: float
    yards_gained: ProbabilitySpace

    down: int
    distance: int
    yards_to_goal: int


def assert_sum(total: float, *X: list[float]):
    assert math.isclose(sum(X), total), " + ".join([str(x) for x in X])


class DriveEngineV2():

    def __init__(
        self,
        plays: FilterList[Play],
        precision: float = 0.000001,
        max_yards_lost: int = -5,
        max_yards_gained: int = 99,
        validate: bool = True,
        separate_redzone: bool = True,
    ):
        # print("Creating Drive Engine ...")

        plays = plays.filter(admin=False, other=False)

        drives = plays.filter(scrimmage=True).split("drive_id")
        drives = [sorted(drive, key=lambda p: p.play_number) for drive in drives.values()]

        drive_success_rates = {}
        for yards_to_goal in range(1, 100):
            drives_here = [d for d in drives if any([p.yards_to_goal <= yards_to_goal for p in d])]
            scoring_drives_here = [d for d in drives_here if any([p.touchdown for p in d])]
            drive_success_rates[yards_to_goal] = len(scoring_drives_here) / len(drives_here)

        min_value = min(drive_success_rates.values())
        drive_success_rates = {y: (value - min_value) / (1.0 - min_value) for y, value in drive_success_rates.items()}
        drive_success_rates[0] = 1.0

        sets_of_downs = []
        for drive in drives:
            for play in drive:
                if play.down == 1:
                    sets_of_downs.append([[], False, False])
                sets_of_downs[-1][0].append(play)
                if play.scoring:
                    sets_of_downs[-1][1] = True
            sets_of_downs[-1][2] = not sets_of_downs[-1][1]

        downs_success_rates = {}
        for down in range(1, 5):
            downs_success_rates[down] = {}
            for distance in range(1, 100):
                sets_of_downs_here = [d for d in sets_of_downs if any([p.distance <= distance and p.down == down for p in d[0]])]
                successful_sets_of_downs_here = [d for d in sets_of_downs_here if not d[2]]
                downs_success_rates[down][distance] = len(successful_sets_of_downs_here) / len(sets_of_downs_here) if len(sets_of_downs_here) > 0 else 0
        
        base_value = downs_success_rates[1][10]
        downs_success_rates = {d: {y: (value - base_value) / (1.0 - base_value) for y, value in down.items()} for d, down in downs_success_rates.items()}

        def drive_success_rate(game):
            return fmean([
                drive_success_rates[sorted([p for p in drive], key=lambda p: p.play_number)[-1].yards_to_goal]
                for drive in game.split("drive_id").values()
            ])

        def game_success_rate(game):
            return sum([
                play_success_rate(play)
                for play in game
            ])

        def play_success_rate(play):
            try:

                if play.kickoff:
                    # TODO: handle kickoff
                    return 0

                if play.turnover:
                    # Turnover
                    # TODO: handle safety
                    if play.scoring and play.yards_to_goal == 100:
                        return -1 * drive_success_rates[min(100 - play.yards_gained, 99)]
                    return -1 * drive_success_rates[play.yards_to_goal]

                if play.punt:
                    # TODO: handle punt
                    return 0

                if play.down == 4 and play.yards_gained < play.distance:
                    # Turnover on downs
                    return -1 * drive_success_rates[play.yards_to_goal]

                if play.touchdown:
                    # Touchdown
                    if play.yards_to_goal == 100:
                        return 1 - drive_success_rates[100 - play.yards_gained]
                    return 1 - drive_success_rates[play.yards_to_goal]

                if play.field_goal_attempt:
                    # Field Goal
                    if play.field_goal_made:
                        if play.yards_to_goal == 100:
                            play.yards_to_goal = play.yards_gained
                        return (3/7) * (1 - drive_success_rates[play.yards_to_goal])
                    else:
                       return -1 * drive_success_rates[play.yards_to_goal]

                if play.pat:
                    # TODO: handle PAT: XP, 2p, defensive 2p, and offensive 1p safety
                    return 0

                if not play.scrimmage:
                    raise Exception("not scrimmage!")

                if play.yards_gained > play.yards_to_goal:
                    # TODO: what to do with these plays? data entry errors
                    return 0

                if play.distance == 0:
                    play.distance = 1

                # Value of getting a first down
                first_and_ten_yardline = min(play.yards_to_goal - play.distance + 10, 99)
                first_down_yardline = play.yards_to_goal - play.distance
                first_down_success_rate = drive_success_rates[first_down_yardline] - drive_success_rates[first_and_ten_yardline]

                # Success rate within this set of downs
                if play.yards_gained >= play.distance:
                    # First down
                    downs_success_rate = 1 - downs_success_rates[play.down][play.distance]
                else:
                    downs_success_rate = downs_success_rates[play.down + 1][play.distance - play.yards_gained] - downs_success_rates[play.down][play.distance]

                # Success rate of extra yards beyond first down
                extra_yards = max(play.yards_gained - play.distance, 0)
                extra_yards_success_rate = drive_success_rates[first_down_yardline - extra_yards] - drive_success_rates[first_down_yardline]

                success_rate = downs_success_rate * first_down_success_rate + extra_yards_success_rate

                return success_rate

            except Exception as e:
                print(play)
                raise e

        # TODO: field position?
        # TODO: split rush and pass
        # TODO: defense and offense contribute to each other via turnovers, defensives scores, field positions, etc.

        games = [(team, sum([play_success_rate(play) for play in game]), max([p.offense_score for p in game]), len(game.split("drive_id"))) for team, plays in plays.split("offense").items() for game in plays.split("game_id").values()]

        for team, success_rate, points, num_drives in games:
            print(f"{team},{success_rate},{points},{num_drives}")

        return

        self.success_rate = AdjustedStat.from_plays(
            plays,
            stat=game_success_rate,
        )

        print("Created Drive Engine...")

    def run(self, possession: Possession, collect_stats: bool = True):
        return 7 * self.success_rate.value(offense=possession.offense, defense=possession.defense)


class FootballEngine(ABC):

    def __init__(
        self,
        plays: FilterList[Play],
        drive_success_rates: dict[int, float],
        downs_success_rates: dict[int, float],
    ):
        self.drive_success_rates = drive_success_rates
        self.downs_success_rates = downs_success_rates
        # self.avg_number_of_drives = fmean([
        #     len(game.split("drive_number"))
        #     for game in plays.split("game_id").values()
        # ]) / 2
        # self.avg_number_of_plays = fmean([
        #     len(game)
        #     for game in plays.split("game_id").values()
        # ]) / 2

        # print(fmean([
        #     len(game.split("drive_id")) for team, plays in plays.split("defense").items() for game in plays.split("game_id").values()
        # ]))
        # print(fmean([
        #     len(game.split("drive_id")) for game in plays.split("game_id").values()
        # ]))
        # for team, team_plays in plays.split("defense").items():
        #     print(team)
        #     for id, game in team_plays.split("game_id").items():
        #         print(len([d for d in game.split("drive_id").values() if all([not p.kickoff for p in d])]))
        #         print(len(plays.split("game_id")[id].split("drive_id")))
        #         for drive in [d for d in game.split("drive_id").values() if all([not p.kickoff for p in d])]:
        #             for play in sorted(drive, key=lambda p: p.play_number):
        #                 print(f"{play.drive_id} | {play.play_number} | {play.play_text}")
        #             print("="*100)
        #             print()
        #             print("="*100)
        #         raise Exception()

        # TODO: average per play (drives?) and multiply by average number of plays in a game to adjust for play speeds (??)

        def num_of_drives(game: FilterList[Play]):
            # Count drives in the game but remove kickoffs as those have offense/defense backwards
            return len([d for d in game.split("drive_id").values() if all([not p.kickoff for p in d])])

        def game_average(plays):
            if len(plays) == 0:
                return 0
            return fmean(plays)

        self.success_rate = AdjustedStat.from_plays(
            plays,
            # stat=lambda game: sum([self.play_success_rate(p) for p in game if self.play_success_rate(p) is not None]) / num_of_drives(game),
            stat=lambda game: game_average([self.play_success_rate(p) for p in game if self.play_success_rate(p) is not None]),
        )

        self.num_plays_per_drive = AdjustedStat.from_plays(
            plays,
            stat=lambda game: sum([1 for p in game if self.play_success_rate(p) is not None]) / num_of_drives(game),
        )

    def run(self, possession: Possession) -> float:
        return self.success_rate.value(offense=possession.offense, defense=possession.defense) * self.num_plays_per_drive.value(offense=possession.offense, defense=possession.defense)

    @abstractmethod
    def play_success_rate(self, play: Play):
        raise NotImplementedError()
