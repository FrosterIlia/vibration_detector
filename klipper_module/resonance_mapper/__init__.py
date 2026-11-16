from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Klipper modules are top-level in ../klipper/klippy (see python.analysis.extraPaths).
    # Imported only for type hints so go-to-definition works; not needed at runtime.
    from configfile import ConfigWrapper
    from gcode import GCodeCommand, GCodeDispatch
    from klippy import Printer


class ResonanceMapper:
    def __init__(self, config: ConfigWrapper):
        self.printer: Printer = config.get_printer()
        gcode: GCodeDispatch = self.printer.lookup_object('gcode')
        gcode.register_command('MAP_HELLO', self.cmd_MAP_HELLO,
                               desc="Check resonance_mapper is loaded")

    def cmd_MAP_HELLO(self, gcmd: GCodeCommand):
        gcmd.respond_info("resonance_mapper alive")

def load_config(config: ConfigWrapper):
    return ResonanceMapper(config)
