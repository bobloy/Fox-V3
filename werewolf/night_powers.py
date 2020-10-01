import logging

from werewolf.role import Role

log = logging.getLogger("red.fox_v3.werewolf.night_powers")


def night_immune(role: Role):
    role.player.alive = True


async def pick_target(role: Role, ctx, data):
    if not role.player.alive:  # FixMe: Game handles this?
        await role.player.send_dm("You're already dead!")
        return None

    target_id = int(data)
    try:
        target = role.game.players[target_id]
    except IndexError:
        target = None

    if target is None:
        await ctx.send("Not a valid ID")
        return None

    return target_id, target
