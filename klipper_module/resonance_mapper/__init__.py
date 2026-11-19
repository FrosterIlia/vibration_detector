from __future__ import annotations
from typing import TYPE_CHECKING
import csv
import os
import time

from extras.resonance_tester import (
    ResonanceTestExecutor, SweepingVibrationsTestGenerator, TestAxis)
from .grid import ScanGrid

from .sensor import (AccelerometerSerial, AccelerometerError,
                     HZ_PER_BIN, N_BINS)

if TYPE_CHECKING:
    from configfile import ConfigWrapper
    from gcode import GCodeCommand, GCodeDispatch
    from klippy import Printer
    from toolhead import ToolHead


class ResonanceMapper:
    def __init__(self, config: ConfigWrapper):
        self.printer: Printer = config.get_printer()

        stepper_x = config.getsection('stepper_x')
        stepper_y = config.getsection('stepper_y')

        min_x = stepper_x.getfloat('position_min', 0.)
        max_x = stepper_x.getfloat('position_max')
        min_y = stepper_y.getfloat('position_min', 0.)
        max_y = stepper_y.getfloat('position_max')
        points_per_axis = config.getint('points_per_axis', 5, minval=2)
        margin = config.getfloat('margin', 10., minval=0.)

        try:
            self.grid = ScanGrid(min_x, min_y, max_x, max_y,
                                 points_per_axis, margin)
        except ValueError as e:
            raise config.error(f"resonance_mapper: {e}")

        self.speed = config.getfloat('speed', 100., above=0.)
        self.settle_time = config.getfloat('settle_time', 0.5, minval=0.)

        self.test_generator = SweepingVibrationsTestGenerator(config)
        self.test_executor = ResonanceTestExecutor(config)
        self.accelerometer = AccelerometerSerial(
            self.printer.get_reactor(),
            config.get('serial_port', '/dev/serial0'),
            config.getint('baud', 115200, minval=9600))

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
            raise gcmd.error(
                "X and Y are not homed, run SET_KINEMATIC_POSITION first")

        points = [self.grid.get_points()[0]]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        gcmd.respond_info(f"{len(points)} points covering "
                          f"X{min(xs):.1f}-{max(xs):.1f} "
                          f"Y{min(ys):.1f}-{max(ys):.1f}")

        resonance_map = {}

        try:
            for i, (x, y) in enumerate(points):
                self._visit_point(gcmd, toolhead, i + 1, len(points), x, y,
                                  resonance_map)
            toolhead.manual_move([points[0][0], points[0][1], None],
                                 self.speed)
            toolhead.wait_moves()
            gcmd.respond_info("done")
        finally:
            if resonance_map:
                path = self._write_csv(resonance_map)
                gcmd.respond_info(f"resonance map saved to {path}")

    def _visit_point(self, gcmd, toolhead, n, total, x, y, resonance_map):
        toolhead.manual_move([x, y, None], self.speed)
        toolhead.wait_moves()
        gcmd.respond_info(f"point {n}/{total} at ({x:.2f}, {y:.2f})")

        reactor = self.printer.get_reactor()
        reactor.pause(reactor.monotonic() + self.settle_time)

        psd_by_axis = {}
        for axis in ('x', 'y'):
            measuring = False
            try:
                self.accelerometer.start_cmd()
                measuring = True
                self.test_generator.prepare_test(gcmd, is_z=False)
                test_seq = self.test_generator.gen_test()
                self.test_executor.run_test(test_seq, TestAxis(axis), gcmd)
                toolhead.wait_moves()
                self.accelerometer.stop_cmd()
                measuring = False
                psd_by_axis[axis] = self.accelerometer.get_psd()
            except AccelerometerError as e:
                raise gcmd.error(f"resonance_mapper: {e}")
            finally:
                if measuring:
                    self.accelerometer.abort()

        resonance_map[(x, y)] = psd_by_axis

    def _write_csv(self, resonance_map):
        out_dir = os.path.expanduser("~/resonance_data")
        os.makedirs(out_dir, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"resonance_map_{stamp}.csv")

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["x_pos", "y_pos", "excite_axis", "bin",
                             "freq_hz", "psd_x", "psd_y", "psd_z"])

            for (x, y), by_axis in resonance_map.items():
                for axis, psd in by_axis.items():
                    assert all(len(a) == N_BINS for a in psd)

                    for b in range(N_BINS):
                        writer.writerow([
                            f"{x:.3f}", f"{y:.3f}", axis, b,
                            f"{b * HZ_PER_BIN:.5f}",
                            f"{psd[0][b]:.7g}", f"{psd[1][b]:.7g}",
                            f"{psd[2][b]:.7g}"])
        return path


def load_config(config: ConfigWrapper):
    return ResonanceMapper(config)
