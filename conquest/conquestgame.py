import pathlib

from conquest.regioner import ConquestMap


class ConquestGame:
    def __init__(self, map_path: pathlib.Path, game_name: str, custom_map_path: pathlib.Path):
        self.blank_map = ConquestMap(map_path)
        self.game_name = game_name
        self.custom_map_path = custom_map_path

    async def save_region(self, region):
        if not self.custom:
            return False
        pass  # TODO: region data saving

    async def start_game(self):
        pass
