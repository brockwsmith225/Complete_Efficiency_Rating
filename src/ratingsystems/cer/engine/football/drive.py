import multiprocessing
import time
from functools import partial
from statistics import fmean
from typing import Callable

from ratingsystems.cer.model import FieldPosition, ProbabilitySpace, Possession
from ratingsystems.cer.util.profile import profile

from .play.playcall import PlaycallEngine, _PlaycallEngine
from .play.scoring import ScoringEngine, _ScoringEngine
from .play.turnover import TurnoverEngine, _TurnoverEngine
from .play.yards import YardsEngine, _YardsEngine, YardsEngineV2


class DriveEngine():

    def __init__(self, plays, precision: float = 0.000001):
        print("Creating Drive Engine ...")

        self.plays = plays
        self.precision = precision

        games = plays.split("game_id")
        teams = {}
        num_drives = []
        points = []
        for game in games:
            num_drives.append(len(game.split("drive_number")))
            points.append(7 * len(game.filter(touchdown=True)) + 3 * len(game.filter(field_goal_made=True))) #+ 2 * len(game.filter(two_point_conversion=True)) + 1 * len(game.filter(extra_point_made=True)))

        self.avg_num_drives = fmean(num_drives) / 2
        print(self.avg_num_drives)
        self.avg_points = fmean(points) / 2
        print(self.avg_points)

        admin_plays = plays.filter(admin=True)
        real_plays = plays.filter(admin=False, other=False)

        self.playcall_engine = _PlaycallEngine(real_plays)
        self.turnover_engine = _TurnoverEngine(real_plays)
        self.scoring_engine = _ScoringEngine(real_plays)
        # self.yards_engine = _YardsEngine(real_plays, max_yards_lost=-25, max_yards_gained=99, probability_cutoff=0.00001)
        self.yards_engine = YardsEngineV2(real_plays, max_yards_lost=-5, max_yards_gained=99, probability_cutoff=0.00001, sampling_size=1000)
        # TODO: penalty engine

        print("Created Drive Engine...")

    def run(self, possession: Possession):
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

        self.yards_engine.prime(possession)

        # with multiprocessing.Pool(16) as pool:
            # TODO: calcuate tempo by expected number of plays run
            # while drive_end_pct < 0.9999999999:
        # while drive_end_pct < 0.9999:
        while True:
            if len(field_positions) == 0:
                break
                raise Exception(f"out of plays, drive end pct: {drive_end_pct}")

            # print(sum([p for p, _ in field_positions]))

            results = ProbabilitySpace({})

            # plays that we have not already simulated
            new_field_positions = [field_position for _, field_position in field_positions if field_position not in plays]
            # print("============================")
            # print(len(plays))
            # print(len(new_field_positions))

            # simulate a play
            for field_position in new_field_positions:
                plays[field_position] = self.simulate_play(field_position, possession.offense, possession.defense)
            # new_plays = pool.map(partial(self.simulate_play, offense=possession.offense, defense=possession.defense), new_field_positions)
            # print(len(new_plays))
            # plays.update({FieldPosition(play.down, play.distance, play.yards_to_goal): play for play in new_plays})
            # print(len(plays))
            # print("============================")

            for play_probability, field_position in field_positions:
                if play_probability < self.precision:
                    continue

                play = plays[field_position]

                drive_end_pct += play.end_pct * play_probability
                expected_points += play.expected_points * play_probability
                results += play.results ** play_probability

                # Other stats
                num_plays += play_probability
                if play.scrimmage_pct > 0:
                    num_rush_plays += play_probability * (play.rush_pct / play.scrimmage_pct)
                    num_pass_plays += play_probability * (play.pass_pct / play.scrimmage_pct)
                    # completions += play_probability * (play. * play.pass_pct / (play.rush_pct + play.pass_pct))
                    # TODO: * (1 - play.end_pct)
                    explosive_plays_10 += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= 10) + play.touchdown_pct if play.yards_to_goal >= 10 else 0.0)
                    explosive_plays_20 += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= 20) + play.touchdown_pct if play.yards_to_goal >= 20 else 0.0)
                    explosive_plays_30 += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= 30) + play.touchdown_pct if play.yards_to_goal >= 30 else 0.0)
                    explosive_plays_40 += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= 40) + play.touchdown_pct if play.yards_to_goal >= 40 else 0.0)
                    if play.down == 3:
                        third_down_conversions += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= play.distance) + play.touchdown_pct)
                        third_down_attempts += play_probability
                    if play.down == 4:
                        fourth_down_conversions += play_probability * ((1 - play.turnover_pct - play.touchdown_pct) * play.yards_gained.probability(lambda x: x >= play.distance) + play.touchdown_pct)
                        fourth_down_attempts += play_probability
                    touchdown_pct += play_probability * play.touchdown_pct
                    field_goal_pct += play_probability * play.fgm_pct

            # account for turnover on downs
            drive_end_pct += results.get(None)
            results.remove(None)

            field_positions = results

        profile.reset()
        # profile.stats()
        # print(drive_end_pct)
        # print(len([fp for fp in field_positions.events() if fp is not None]))
        possession.end_pct = drive_end_pct
        possession.expected_points = expected_points / drive_end_pct

        # Other stats
        possession.num_plays = num_plays / drive_end_pct
        possession.rush_pct = num_rush_plays / num_plays
        possession.pass_pct = num_pass_plays / num_plays
        possession.explosive_play_10_pct = explosive_plays_10 / num_plays / drive_end_pct
        possession.explosive_play_20_pct = explosive_plays_20 / num_plays / drive_end_pct
        possession.explosive_play_30_pct = explosive_plays_30 / num_plays / drive_end_pct
        possession.explosive_play_40_pct = explosive_plays_40 / num_plays / drive_end_pct
        possession.third_down_conversion_pct = third_down_conversions / third_down_attempts / drive_end_pct
        possession.fourth_down_conversion_pct = fourth_down_conversions / fourth_down_attempts / drive_end_pct
        possession.touchdown_pct = touchdown_pct / drive_end_pct
        possession.field_goal_pct = field_goal_pct / drive_end_pct

        # print(f"Ran Drive Engine after {time.time() - starttime} seconds")

    @profile
    def simulate_play(self, field_position: FieldPosition, offense, defense):
        play = Possession(offense=offense, defense=defense)

        # set play position
        play.down = field_position.down
        play.distance = field_position.distance
        play.yards_to_goal = field_position.yards_to_goal

        # determine the playcall for this play (run/pass/punt/fga)
        self.playcall_engine.run(play)

        # determine chance of a turnover on this play
        self.turnover_engine.run(play)

        # determine chance of a score on this play
        self.scoring_engine.run(play)

        # determine yards gained on this play
        self.yards_engine.run(play)

        # TODO: penalties?

        play.end_pct = play.punt_pct + play.fga_pct + play.scrimmage_pct * (play.turnover_pct + play.touchdown_pct)
        play.expected_points = 7 * play.touchdown_pct + 3 * play.fgm_pct
        play.results = field_position + play.yards_gained ** (1 - play.end_pct)

        return play


class DriveEngineV2():

    def __init__(self, plays):
        pass

    def run(self, possession):
        pass
