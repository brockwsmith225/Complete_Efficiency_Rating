import cfbd
import math
import networkx as nx
import numpy as np
import json
from statistics import fmean, mean
from scipy.stats import norm, skewnorm, beta
from functools import partial

# from cfbd.models.play import Play

from ratingsystems.common.model.rating import Rating

from ratingsystems.cer import CompleteEfficiencyRatingSystem
from ratingsystems.cer.model import FilterList, CFBTeam, Possession, Play
from ratingsystems.cer.engine.football.drive import DriveEngine

def main(fetch_data = True):
    if fetch_data:
        configuration = cfbd.Configuration()
        configuration.api_key['Authorization'] = ''
        configuration.api_key_prefix['Authorization'] = 'Bearer'
        games_api = cfbd.GamesApi(cfbd.ApiClient(configuration))

        games = []
        year = 2024
        # for week in range(1, 13):
        #     print(week)
        #     games.extend(games_api.get_games(year, week=week, division="fbs", season_type="both"))
        games.extend(games_api.get_games(year, division="fbs", season_type="both"))
        # games.extend(games_api.get_games(2024, division="fcs"))
    #     with open("2024.games", "w") as f:
    #         pickle.dump(games, f)
    # else:
    #     with open("2024.games", "r") as f:
    #         games = pickle.load(f)

    cer = CompleteEfficiencyRatingSystem(
        
    )
    cer_rating = cer.rate(games)
    # rating = cer.rate(games, seed=rating)
    r = 1
    # offensive_rankings = {t.name: i + 1 for i, t in enumerate(Rating.rank(rating.offense))}
    # defensive_rankings = {t.name: i + 1 for i, t in enumerate(Rating.rank(rating.defense))}
    for team in Rating.rank(cer_rating):
        # wins = len([e for e in wins_graph.in_edges(nbunch=team, data=True) if e[0] != team])
        # losses = len([e for e in wins_graph.out_edges(nbunch=team, data=True) if e[1] != team])
        # print(f"({r}) {team} ({wins}-{losses}): {round(rating * 10000)} | {round(wins_ratings[team] * 10000)} | {round(losses_ratings[team] * 10000)}")
        # print(f"({r}) {team.name}: {team.rating.formatted()} | {team.offensive_rating.formatted()} ({offensive_rankings[team.name]}) | {team.defensive_rating.formatted()} ({defensive_rankings[team.name]})")
        print(f"({r}) {team.name}: {team.rating.formatted()} | {team.offense.rating.formatted()} | {team.defense.rating.formatted()}")
        r += 1


def cfb(fetch_data = True):
    print("Gathering data...")
    year = 2025
    if fetch_data:
        print("Fetching data...")
        configuration = cfbd.Configuration(
            access_token=''
        )
        plays_api = cfbd.PlaysApi(cfbd.ApiClient(configuration))

        plays = []
        for week in range(1, 17):
            plays.extend(plays_api.get_plays(year, week, classification="fbs", season_type="both"))
            # plays.extend(plays_api.get_plays(year, week, team="Georgia Tech", classification="fbs", season_type="both"))

        with open(f"cfb-{year}.json", "w") as f:
            json.dump([play.to_dict() for play in plays], f)

        plays = [Play.from_dict(play.to_dict()) for play in plays]
        print("Fetched data")

    else:
        with open(f"cfb-{year}.json", "r") as f:
            plays = [Play.from_dict(play) for play in json.load(f)]
    print("Gathered data")

    # print("\n".join(set([play.play_type for play in plays])))
    # print("\n".join([play.play_text for play in plays if play.play_type == "Uncategorized"]))
    # print("\n".join([str((play.offense, play.play_type, play.play_text)) for play in plays if "Fumble" in play.play_type]))

    # teams = {}
    # team_stats = {}
    # team_names = ["Ohio State", 'Oregon', 'Purdue', 'Akron', 'Texas', 'Penn State', 'Notre Dame', 'Western Michigan', 'Marshall', 'Michigan State', 'Indiana', 'Iowa', 'Michigan', 'Nebraska', 'Northwestern', 'Tennessee']

    plays = FilterList(plays)
    # for team in team_names:
    #     team_stats[team] = {}
    #     for opponent in set([p.defense for p in plays.filter(offense=team)]):
    #         team_stats[team][opponent] = {"offense": {}, "defense": {}}
    #         team_stats[team][opponent]["offense"]["run_rate"] = len(plays.filter(offense=team, defense=opponent, rushing=True)) / len(plays.filter(offense=team, defense=opponent, scrimmage=True))
    #         team_stats[team][opponent]["defense"]["run_rate"] = len(plays.filter(defense=team, offense=opponent, rushing=True)) / len(plays.filter(defense=team, offense=opponent, scrimmage=True))

    # for team in team_names:
    #     opponents = list(team_stats[team].keys())
    #     for stat in team_stats[team][opponents[0]]["offense"]:
    #         team_stats[team]["avg"] = {"offense": {}, "defense": {}}
    #         team_stats[team]["avg"]["offense"][stat] = avg([team_stats[team][o]["offense"][stat] for o in opponents])
    #         team_stats[team]["avg"]["defense"][stat] = avg([team_stats[team][o]["defense"][stat] for o in opponents])
    #         team_stats[team]["stdev"] = {"offense": {}, "defense": {}}
    #         team_stats[team]["stdev"]["offense"][stat] = stdev([team_stats[team][o]["offense"][stat] for o in opponents])
    #         team_stats[team]["stdev"]["defense"][stat] = stdev([team_stats[team][o]["offense"][stat] for o in opponents])

    # print(team_stats["Ohio State"]["avg"]["offense"]["run_rate"])
    
    # for team in team_stats:
    #     teams[team] = {"offense": {}, "defense": {}}
    #     for opponent in team_stats[team]:
    #         if opponent in ["avg", "stdev"]:
    #             continue
    #         for stat in team_stats[team][opponent]["offense"]:
    #             print(team)
    #             print(team_stats[team][opponent]["offense"][stat])
    #             print(opponent)
    #             print(team_stats[opponent]["avg"]["defense"][stat])
    #             print("---------------------------")

    # print([p.down for p in plays.filter(field_goal_attempt=True)])

    # ohio_state = CFBTeam("Ohio State", FilterList(plays))
    # drive = Possession(ohio_state.plays.filter(offense=ohio_state.name), None)
    # drive = Possession(ohio_state.plays.filter(defense=ohio_state.name), None)
    # DriveEngine(plays).run(drive)
    # print(drive.__dict__)

    # georgia_tech = CFBTeam("Georgia Tech", plays)
    # drive = Possession(georgia_tech.filter(offense=georgia_tech.name), None)
    # DriveEngine.run(drive)
    # print(drive.__dict__)

    fbs = {'Sun Belt', 'Mid-American', 'FBS Independents', 'Conference USA', 'Big 12', 'Big Ten', 'Pac-12', 'Mountain West', 'SEC', 'ACC', 'American Athletic'}

    plays = [p for p in plays if p.offense_conference in fbs and p.defense_conference in fbs]

    teams = set([p.offense for p in plays])

    # drive_engine = DriveEngine(plays)
    # for t in teams:
    #     team = CFBTeam(t, FilterList(plays))
    #     offense = Possession(team.plays.filter(offense=t), None)
    #     defense = Possession(team.plays.filter(defense=t), None)
    #     drive_engine.run(offense)
    #     drive_engine.run(defense)
    #     print(f"{t},{offense.expected_points - defense.expected_points},{offense.expected_points},{defense.expected_points}")

    plays = FilterList(plays)

    # scrimmage_plays = plays.filter(scrimmage=True)
    # print(sum([p.yards_gained for p in scrimmage_plays]) / len(scrimmage_plays))
    # print(len([p for p in scrimmage_plays if p.yards_gained >= 10]) / len(scrimmage_plays))
    # print(len([p for p in scrimmage_plays if p.yards_gained >= 20]) / len(scrimmage_plays))
    # print(len([p for p in scrimmage_plays if p.yards_gained >= 30]) / len(scrimmage_plays))
    # print(len([p for p in scrimmage_plays if p.yards_gained >= 40]) / len(scrimmage_plays))
    # third_down_plays = scrimmage_plays.filter(down=3)
    # print(len([p for p in third_down_plays if p.yards_gained >= p.distance or p.touchdown]) / len(third_down_plays))

    # yards_plays = scrimmage_plays.filter(turnover=False, penalty=False)
    # yards_plays = yards_plays.filter(rushing=True)
    # yards_plays = FilterList([p for p in yards_plays if p.yards_gained >= -5])

    # team_distributions = []
    # # for team in ["Ohio State"]:
    # for team in ["Ohio State", "Indiana", "Georgia Tech", "Wake Forest"]:
    #     team_plays = yards_plays.filter(offense=team)
    #     # for yards_gained in range(-20, 51):
    #     #     print(f'"{yards_gained}","{len([p for p in yards_plays if p.yards_gained == yards_gained]) / len(yards_plays)}"')

    #     # defenses_plays = yards_plays.split("defense")
    #     # loc, scale = norm.fit([p.yards_gained for p in yards_plays])
    #     # total_distribution = partial(norm.pdf, loc=loc, scale=scale)
    #     # defense_distributions = []
    #     # for _, defense_plays in defenses_plays.items():
    #     #     loc, scale = norm.fit([p.yards_gained for p in defense_plays])
    #     #     defense_distributions.append(partial(norm.pdf, loc=loc, scale=scale))
    #     # for yards_gained in range(-20, 51):
    #     #     print(f'"{yards_gained}","{total_distribution(yards_gained)}"', end=",")
    #     #     for defense_distribution in defense_distributions:
    #     #         print(f'"{defense_distribution(yards_gained)}"', end=",")
    #     #     print()

    #     # defenses_plays = yards_plays.split("defense")
    #     # a, b, loc, scale = skewnorm.fit([p.yards_gained for p in yards_plays])
    #     # total_distribution = partial(skewnorm.pdf, a=a, b, loc=loc, scale=scale)
    #     # defense_distributions = []
    #     # for _, defense_plays in defenses_plays.items():
    #     #     a, b, loc, scale = skewnorm.fit([p.yards_gained for p in defense_plays])
    #     #     defense_distributions.append(partial(skewnorm.pdf, a=a, b, loc=loc, scale=scale))
    #     # for yards_gained in range(-20, 51):
    #     #     print(f'"{yards_gained}","{total_distribution(yards_gained)}"', end=",")
    #     #     for defense_distribution in defense_distributions:
    #     #         print(f'"{defense_distribution(yards_gained)}"', end=",")
    #     #     print()

    #     samples = 10000
    #     max_shape = None

    #     # defenses_plays = yards_plays.split("defense")
    #     # shape, loc, scale = skewnorm.fit([p.yards_gained for p in yards_plays])
    #     # total_distribution = partial(skewnorm.pdf, a=shape, loc=loc, scale=scale)
    #     # defense_distributions = []
    #     # adjusted_distributions = []
    #     # for _, defense_plays in defenses_plays.items():
    #     #     dshape, dloc, dscale = skewnorm.fit([p.yards_gained for p in defense_plays])
    #     #     defense_distributions.append(partial(skewnorm.pdf, a=dshape, loc=dloc, scale=dscale))
    #     #     offense = skewnorm.rvs(a=shape, loc=loc, scale=scale, size=samples)
    #     #     defense = skewnorm.rvs(a=dshape, loc=dloc, scale=dscale, size=samples)
    #     #     pshape, ploc, pscale = skewnorm.fit([p.yards_gained for p in plays.filter(turnover=False, penalty=False, rushing=True)])
    #     #     population = skewnorm.rvs(a=shape, loc=loc, scale=scale, size=samples)
    #     #     dshape, dloc, dscale = skewnorm.fit([defense[i] - offense[i] + population[i] for i in range(samples)])
    #     #     adjusted_distributions.append(partial(skewnorm.pdf, a=dshape, loc=dloc, scale=dscale))
    #     #     break
    #     # for yards_gained in range(-20, 51):
    #     #     print(f'"{yards_gained}","{total_distribution(yards_gained)}"', end=",")
    #     #     print(f'"{defense_distributions[0](yards_gained)}"', end=",")
    #     #     print(f'"{adjusted_distributions[0](yards_gained)}"', end=",")
    #     #     print()

    #     # Population distribution of yards_gained for the season
    #     pshape, ploc, pscale = skewnorm.fit([p.yards_gained for p in yards_plays])
    #     print((pshape, ploc, pscale))

    #     opponents = set(team_plays.split("defense").keys())
    #     print(opponents)
    #     games = []
    #     adjusted_distributions = []
    #     season = []
    #     # for opponent in opponents:
    #     #     # Offense's distribution of yards_gained for each game
    #     #     adjusted_distributions.append(lambda y: len([p for p in team_plays.filter(defense=opponent) if p.yards_gained == y]) / len(team_plays.filter(defense=opponent)))
    #     #     shape, loc, scale = skewnorm.fit([p.yards_gained for p in team_plays.filter(defense=opponent)])
    #     #     print((shape, loc, scale))
    #     #     if max_shape and shape > max_shape:
    #     #         shape, loc, scale = skewnorm.fit([p.yards_gained for p in team_plays.filter(defense=opponent)], f0=max_shape)
    #     #         print((shape, loc, scale))
    #     #     offense = skewnorm.rvs(a=shape, loc=loc, scale=scale, size=samples)
    #     #     adjusted_distributions.append(partial(skewnorm.pdf, a=shape, loc=loc, scale=scale))
    #     #     # Defenses' distributions of yards_gained for the season
    #     #     shape, loc, scale = skewnorm.fit([p.yards_gained for p in yards_plays.filter(defense=opponent)])
    #     #     print((shape, loc, scale))
    #     #     defense = skewnorm.rvs(a=shape, loc=loc, scale=scale, size=samples)
    #     #     adjusted_distributions.append(partial(skewnorm.pdf, a=shape, loc=loc, scale=scale))
    #     #     games.append((offense, defense))
    #     #     game = [offense[i] / defense[i] for i in range(samples)]
    #     #     # game.sort()
    #     #     season.extend(game)
    #     #     shape, loc, scale = skewnorm.fit(game)
    #     #     print((shape, loc, scale))
    #     #     adjusted_distributions.append(partial(skewnorm.pdf, a=shape, loc=loc, scale=scale))
    #     shape, loc, scale = skewnorm.fit([p.yards_gained for p in team_plays])
    #     glocs = []
    #     for opponent in opponents:
    #         # Offense's distribution of yards_gained for each game
    #         oshape, oloc, oscale = skewnorm.fit([p.yards_gained for p in team_plays.filter(defense=opponent)])
    #         if max_shape and oshape > max_shape:
    #             oshape, oloc, oscale = skewnorm.fit([p.yards_gained for p in team_plays.filter(defense=opponent)], f0=max_shape)
    #         offense = skewnorm.rvs(a=oshape, loc=oloc, scale=oscale, size=samples)
    #         adjusted_distributions.append(partial(skewnorm.pdf, a=oshape, loc=oloc, scale=oscale))
    #         # Defenses' distributions of yards_gained for the season
    #         dshape, dloc, dscale = skewnorm.fit([p.yards_gained for p in yards_plays.filter(defense=opponent)])
    #         defense = skewnorm.rvs(a=dshape, loc=dloc, scale=dscale, size=samples)
    #         adjusted_distributions.append(partial(skewnorm.pdf, a=dshape, loc=dloc, scale=dscale))
    #         game = [offense[i] - defense[i] for i in range(samples)]
    #         season.extend(game)
    #         gshape, gloc, gscale = skewnorm.fit(game)
    #         adjusted_distributions.append(partial(skewnorm.pdf, a=gshape, loc=gloc, scale=gscale))
    #         glocs.append(gloc)

    #     sshape, sloc, sscale = skewnorm.fit(season)
    #     season_distribution = partial(skewnorm.pdf, a=sshape, loc=sloc, scale=sscale)
    #     season = skewnorm.rvs(a=sshape, loc=sloc, scale=scale, size=samples)
    #     population = skewnorm.rvs(a=pshape, loc=ploc, scale=pscale, size=samples)
    #     fshape, floc, fscale = skewnorm.fit([season[i] + population[i] for i in range(samples)])
    #     final_distribution = partial(skewnorm.pdf, a=fshape, loc=floc, scale=fscale)
    #     # final_distribution = partial(skewnorm.pdf, a=shape, loc=sloc + ploc, scale=scale)
    #     # shape, loc, scale = skewnorm.fit([p.yards_gained for p in team_plays])
    #     real_distribution = partial(skewnorm.pdf, a=shape, loc=loc, scale=scale)
    #     team_distributions.append(real_distribution)
    #     # team_distributions.append(season_distribution)
    #     team_distributions.append(final_distribution)

    #     # pa, pb, ploc, pscale = beta.fit([p.yards_gained for p in yards_plays])
    #     # print((pa, pb, ploc, pscale))

    #     # a, b, loc, scale = beta.fit([p.yards_gained for p in team_plays])
    #     # glocs = []
    #     # for opponent in opponents:
    #     #     # Offense's distribution of yards_gained for each game
    #     #     oa, ob, oloc, oscale = beta.fit([p.yards_gained for p in team_plays.filter(defense=opponent)])
    #     #     # if max_a, b and oa, b > max_a, b:
    #     #     #     oa, b, oloc, oscale = beta.fit([p.yards_gained for p in team_plays.filter(defense=opponent)], f0=max_a, b)
    #     #     offense = beta.rvs(a=oa, b=ob, loc=oloc, scale=oscale, size=samples)
    #     #     adjusted_distributions.append(partial(beta.pdf, a=oa, b=ob, loc=oloc, scale=oscale))
    #     #     # Defenses' distributions of yards_gained for the season
    #     #     da, db, dloc, dscale = beta.fit([p.yards_gained for p in yards_plays.filter(defense=opponent)])
    #     #     defense = beta.rvs(a=da, b=db, loc=dloc, scale=dscale, size=samples)
    #     #     adjusted_distributions.append(partial(beta.pdf, a=da, b=db, loc=dloc, scale=dscale))
    #     #     game = [offense[i] - defense[i] for i in range(samples)]
    #     #     season.extend(game)
    #     #     ga, gb, gloc, gscale = beta.fit(game)
    #     #     adjusted_distributions.append(partial(beta.pdf, a=ga, b=gb, loc=gloc, scale=gscale))
    #     #     glocs.append(gloc)

    #     # sa, sb, sloc, sscale = beta.fit(season)
    #     # season_distribution = partial(beta.pdf, a=sa, b=sb, loc=sloc, scale=sscale)
    #     # season = beta.rvs(a=sa, b=sb, loc=sloc, scale=scale, size=samples)
    #     # population = beta.rvs(a=pa, b=pb, loc=ploc, scale=pscale, size=samples)
    #     # fa, fb, floc, fscale = beta.fit([season[i] + population[i] for i in range(samples)])
    #     # final_distribution = partial(beta.pdf, a=fa, b=fb, loc=floc, scale=fscale)
    #     # # final_distribution = partial(beta.pdf, a=a, b=b, loc=sloc + ploc, scale=scale)
    #     # # a, b, loc, scale = beta.fit([p.yards_gained for p in team_plays])
    #     # real_distribution = partial(beta.pdf, a=a, b=b, loc=loc, scale=scale)
    #     # team_distributions.append(real_distribution)
    #     # # team_distributions.append(season_distribution)
    #     # team_distributions.append(final_distribution)

    #     # for yards_gained in range(-20, 51):
    #     #     print(f'"{yards_gained}"', end=",")
    #     #     for adjusted_distribution in adjusted_distributions:
    #     #         print(f'"{adjusted_distribution(yards_gained)}"', end=",")
    #     #     # print(f'"{season_distribution(yards_gained)}"', end=",")
    #     #     print(f'"{final_distribution(yards_gained)}"', end=",")
    #     #     print()

    # for yards_gained in range(-5, 51):
    #     print(f'"{yards_gained}"', end=",")
    #     for team_distribution in team_distributions:
    #         print(f'"{team_distribution(yards_gained)}"', end=",")
    #     print()

    # defenses_plays = yards_plays.split("defense")
    # loc, scale = norm.fit([p.yards_gained for p in yards_plays])
    # total_distribution = partial(norm.pdf, loc=loc, scale=scale)
    # defense_distributions = []
    # adjusted_distributions = []
    # for _, defense_plays in defenses_plays.items():
    #     dloc, dscale = norm.fit([p.yards_gained for p in defense_plays])
    #     defense_distributions.append(partial(norm.pdf, loc=dloc, scale=dscale))
    #     dloc, dscale = norm.fit(norm.)
    #     adjusted_distributions.append()
    #     break
    # for yards_gained in range(-20, 51):
    #     print(f'"{yards_gained}","{total_distribution(yards_gained)}"', end=",")
    #     print(f'"{defense_distributions[0](yards_gained)}"', end=",")
    #     print(f'"{adjusted_distributions[0](yards_gained)}"', end=",")
    #     print()

    # return

    # scrimmage_plays = plays.filter(rushing=True)#, offense="Ohio State")
    # # scrimmage_plays = FilterList([p for p in scrimmage_plays if p.yards_to_goal > 20])
    # # defenses = set([p.defense for p in scrimmage_plays])
    # # for down in range(1, 5):
    # #     plays = scrimmage_plays.filter(down=down)
    # #     print(f"{down},", end="")
    # # for distance in range(1, 26):
    # #     plays = scrimmage_plays.filter(distance=distance)
    # #     print(f"{distance},", end="")
    # # for yards_to_goal in range(1, 100):
    # #     plays = scrimmage_plays.filter(yards_to_goal=yards_to_goal)
    # #     print(f"{yards_to_goal},", end="")
    # for yards_gained in range(-15, 100):
    #     plays = scrimmage_plays.filter(yards_gained=yards_gained)
    #     print(f"{yards_gained},", end="")
    #     for defense in {"test"}:
    #         print(f"{len(plays) if len(plays) > 0 else ''}", end="")
    #         # print(f"{stdev([p.yards_gained for p in plays]) if len(plays) > 0 else ''}", end="")
    #     print()

    # plays = plays.filter(offense="Ohio State") + plays.filter(defense="Ohio State")

    # for play in plays.filter(play_type="Extra Point Missed"):
    # for play in plays.filter(touchdown=True):
    # for play in plays.filter(down=0, scoring=True, yards_gained=1):
        # print(play.play_text)

    print("Preprocessing data ...")
    drive_engine = DriveEngine(plays)
    print("Preprocessed data")

    finished_teams = """""".split("\n")

    for team in teams:
        if team in finished_teams:
            continue
        offense = Possession(team, None)
        defense = Possession(None, team)
        drive_engine.run(offense)
        drive_engine.run(defense)
        print(
            f"{team},"
            f"{(offense.expected_points - defense.expected_points) * drive_engine.avg_num_drives},"
            f"{offense.expected_points - defense.expected_points},"
            f"{offense.expected_points * drive_engine.avg_num_drives},"
            f"{offense.expected_points},"
            f"{defense.expected_points * drive_engine.avg_num_drives},"
            f"{defense.expected_points},"
            f"{offense.end_pct},"
            f"{offense.num_plays},"
            f"{offense.rush_pct},"
            f"{offense.pass_pct},"
            f"{offense.explosive_play_10_pct},"
            f"{offense.explosive_play_20_pct},"
            f"{offense.explosive_play_30_pct},"
            f"{offense.explosive_play_40_pct},"
            f"{offense.third_down_conversion_pct},"
            f"{offense.fourth_down_conversion_pct},"
            f"{offense.touchdown_pct},"
            f"{offense.field_goal_pct},"
            f"{defense.end_pct},"
            f"{defense.num_plays},"
            f"{defense.rush_pct},"
            f"{defense.pass_pct},"
            f"{defense.explosive_play_10_pct},"
            f"{defense.explosive_play_20_pct},"
            f"{defense.explosive_play_30_pct},"
            f"{defense.explosive_play_40_pct},"
            f"{defense.third_down_conversion_pct},"
            f"{defense.fourth_down_conversion_pct},"
            f"{defense.touchdown_pct},"
            f"{defense.field_goal_pct}"
        )


def avg(items: list):
    return sum(items) / len(items)


def stdev(items: list):
    average = avg(items)
    return math.sqrt(sum([pow(v - average, 2) for v in items]) / len(items))


def zscore(value: float, mean: float, stdev: float) -> float:
    return (value - mean) / stdev


if __name__ == "__main__":
    cfb(fetch_data=False)
