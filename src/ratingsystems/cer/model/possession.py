from .team import CFBTeam

class Possession:

    def __init__(self, offense: CFBTeam, defense: CFBTeam):
        self.offense = offense
        self.defense = defense
