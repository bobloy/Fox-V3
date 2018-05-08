from werewolf.role import Role


def night_immune(role: Role):
    role.player.alive = True
