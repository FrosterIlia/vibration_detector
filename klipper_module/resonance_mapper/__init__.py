from __future__ import annotations
from typing import TYPE_CHECKING

from .grid import ScanGrid

if TYPE_CHECKING:
    from configfile import ConfigWrapper
    from gcode import GCodeCommand, GCodeDispatch
    from klippy import Printer
    from toolhead import ToolHead


class ResonanceMapper:
    def __init__(self, config: ConfigWrapper):
        self.printer: Printer = config.get_printer()
        self.grid = ScanGrid(config)
        self.speed = config.getfloat('speed', 100., above=0.)
        self.settle_time = config.getfloat('settle_time', 0.5, minval=0.)
        gcode: GCodeDispatch = self.printer.lookup_object('gcode')
        gcode.register_command('MAP_HELLO', self.cmd_MAP_HELLO,
                               desc="Check resonance_mapper is loaded")
        gcode.register_command('MAP_GRID', self.cmd_MAP_GRID,
                               desc="Print the scan grid points")
        gcode.register_command(
            'MAP_RESONANCES', self.cmd_MAP_RESONANCES, desc="Measure resonance mesh")

    def cmd_MAP_HELLO(self, gcmd: GCodeCommand):
        gcmd.respond_info("resonance_mapper alive")

    def cmd_MAP_GRID(self, gcmd: GCodeCommand):
        points = self.grid.get_points()
        gcmd.respond_info(str(points))

    def cmd_MAP_RESONANCES(self, gcmd: GCodeCommand):
        toolhead: ToolHead = self.printer.lookup_object('toolhead')
        reactor = self.printer.get_reactor()
        homed = toolhead.get_status(reactor.monotonic())['homed_axes']
        if 'x' not in homed or 'y' not in homed:
            raise gcmd.error("X and Y are not homed, run SET_KINEMATIC_POSITION first")

        points = self.grid.get_points()
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        gcmd.respond_info(f"{len(points)} points covering "
                          f"X{min(xs):.1f}-{max(xs):.1f} "
                          f"Y{min(ys):.1f}-{max(ys):.1f}")

        for i, (x, y) in enumerate(points):
            self._visit_point(gcmd, toolhead, i + 1, len(points), x, y)

        toolhead.manual_move([points[0][0], points[0][1], None], self.speed)
        toolhead.wait_moves()
        gcmd.respond_info("done")

    def _visit_point(self, gcmd, toolhead, n, total, x, y):
        toolhead.manual_move([x, y, None], self.speed)
        toolhead.wait_moves()
        gcmd.respond_info(f"point {n}/{total} at ({x:.2f}, {y:.2f})")
        reactor = self.printer.get_reactor()
        reactor.pause(reactor.monotonic() + self.settle_time)


def load_config(config: ConfigWrapper):
    return ResonanceMapper(config)
