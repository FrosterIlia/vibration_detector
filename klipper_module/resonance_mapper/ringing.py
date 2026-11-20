import csv
import os
import time

import numpy as np

from . import analysis
from .sensor import AccelerometerError, CAPTURE_SECONDS, FS

PREROLL = 0.3


class RingingTester:
    def __init__(self, config, mapper):
        self.printer = config.get_printer()
        self.mapper = mapper
        self.accelerometer = mapper.accelerometer

        self.dist = config.getfloat('ringing_distance', 40., above=0.)
        self.speed = config.getfloat('ringing_speed', 300., above=0.)
        self.accel = config.getfloat('ringing_accel', 3000., above=0.)
        self.repeats = config.getint('ringing_repeats', 4, minval=1)
        self.dwell = config.getfloat('ringing_dwell', 0.6, above=0.)
        self.window = config.getfloat('ringing_window', 0.4, above=0.)
        self.offset = config.getfloat('ringing_offset', 0.03, minval=0.)
        if self.dwell < self.offset + self.window:
            raise config.error(
                "ringing_dwell must be >= ringing_offset + ringing_window")

        self.printer.lookup_object('gcode').register_command(
            'RINGING_TEST', self.cmd_RINGING_TEST,
            desc="Measure ringing after sharp stops, shaper off vs on")

    def cmd_RINGING_TEST(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        gcode = self.printer.lookup_object('gcode')
        reactor = self.printer.get_reactor()
        status = toolhead.get_status(reactor.monotonic())
        if 'x' not in status['homed_axes'] or 'y' not in status['homed_axes']:
            raise gcmd.error("X and Y are not homed")
        shaper = self.printer.lookup_object('input_shaper', None)
        if shaper is None:
            raise gcmd.error("RINGING_TEST needs an [input_shaper] section")

        grid = self.mapper.grid
        x = gcmd.get_float('X', (grid.min_x + grid.max_x) / 2)
        y = gcmd.get_float('Y', (grid.min_y + grid.max_y) / 2)
        axes = gcmd.get('AXIS', 'xy').lower()
        if not axes or any(a not in 'xy' for a in axes):
            raise gcmd.error("AXIS must be x, y or xy")
        dist = gcmd.get_float('DIST', self.dist, above=0.)
        speed = gcmd.get_float('SPEED', self.speed, above=0.)
        accel = gcmd.get_float('ACCEL', self.accel, above=0.)
        repeats = gcmd.get_int('REPEATS', self.repeats, minval=1)
        conditions = {'off': ['off'], 'current': ['on'],
                      'both': ['off', 'on']}.get(gcmd.get('SHAPER', 'both').lower())
        if conditions is None:
            raise gcmd.error("SHAPER must be off, current or both")

        moves, ta, tc, duration = analysis.plan(dist, speed, accel,
                                                self.dwell, repeats)
        if duration + PREROLL + 1. > CAPTURE_SECONDS:
            raise gcmd.error(f"sequence takes {duration:.1f}s, too long for "
                             f"the {CAPTURE_SECONDS}s capture, lower REPEATS")

        gcmd.respond_info(f"ringing test at ({x:.1f}, {y:.1f}): "
                          f"{dist}mm @ {speed}mm/s, accel {accel}, "
                          f"decel time {ta * 1000:.0f}ms")
        gcode.run_script_from_command("SET_INPUT_SHAPER")

        restore = ("SET_VELOCITY_LIMIT VELOCITY=%.3f ACCEL=%.3f "
                   "MINIMUM_CRUISE_RATIO=%.3f" % (
                       status['max_velocity'], status['max_accel'],
                       status['minimum_cruise_ratio']))

        out_dir = os.path.expanduser("~/resonance_data")
        os.makedirs(out_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        rows = []

        try:
            toolhead.manual_move([x, y, None], self.mapper.speed)
            toolhead.wait_moves()
            gcode.run_script_from_command(
                f"SET_VELOCITY_LIMIT VELOCITY={max(speed, status['max_velocity'])} "
                f"ACCEL={accel} MINIMUM_CRUISE_RATIO=0")

            for axis in axes:
                means = {}
                for cond in conditions:
                    if cond == 'off':
                        shaper.disable_shaping()
                    else:
                        shaper.enable_shaping()

                    samples = self._record(toolhead, axis, x, y, dist,
                                           speed, repeats)
                    name = f"ringing_{stamp}_{axis}_{cond}.npz"
                    np.savez(os.path.join(out_dir, name), samples=samples,
                             fs=FS, dist=dist, speed=speed, accel=accel,
                             dwell=self.dwell, repeats=repeats)

                    try:
                        res, ax, fs_est = analysis.analyze(
                            samples, FS, moves, ta, tc, accel,
                            self.offset, self.window)
                    except ValueError as e:
                        raise gcmd.error(f"ringing analysis failed: {e}")

                    for r in res:
                        rows.append([f"{x:.3f}", f"{y:.3f}", axis, cond,
                                     r['direction'], r['repeat'], accel,
                                     speed, dist, f"{r['rms_along']:.1f}",
                                     f"{r['rms_cross']:.1f}",
                                     f"{r['rms_total']:.1f}", name])
                    along = [r['rms_along'] for r in res]
                    means[cond] = np.mean(along)
                    gcmd.respond_info(
                        f"{axis} shaper {cond}: ringing {np.mean(along):.0f} "
                        f"+- {np.std(along):.0f} mm/s^2 over {len(res)} stops "
                        f"(sensor axis {'xyz'[ax]}, fs ~{fs_est:.0f}Hz)")

                if 'off' in means and 'on' in means:
                    change = (means['on'] / means['off'] - 1) * 100
                    gcmd.respond_info(f"{axis}: shaper changes ringing "
                                      f"by {change:+.0f}%")
        finally:
            shaper.enable_shaping()
            gcode.run_script_from_command(restore)
            if rows:
                path = os.path.join(out_dir, f"ringing_{stamp}.csv")
                with open(path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["x_pos", "y_pos", "axis", "shaper",
                                     "direction", "repeat", "accel", "speed",
                                     "dist", "rms_along", "rms_cross",
                                     "rms_total", "capture"])
                    writer.writerows(rows)
                gcmd.respond_info(f"ringing results saved to {path}")

    def _record(self, toolhead, axis, x, y, dist, speed, repeats):
        reactor = self.printer.get_reactor()
        reactor.pause(reactor.monotonic() + self.mapper.settle_time)
        far = [x + dist, y, None] if axis == 'x' else [x, y + dist, None]

        try:
            self.accelerometer.start_capture()
            toolhead.dwell(PREROLL)
            for _ in range(repeats):
                toolhead.manual_move(far, speed)
                toolhead.dwell(self.dwell)
                toolhead.manual_move([x, y, None], speed)
                toolhead.dwell(self.dwell)
            toolhead.wait_moves()
            self.accelerometer.stop_cmd()
            return self.accelerometer.get_capture()
        except AccelerometerError as e:
            self.accelerometer.abort()
            raise self.printer.command_error(f"resonance_mapper: {e}")
        except Exception:
            self.accelerometer.abort()
            raise
