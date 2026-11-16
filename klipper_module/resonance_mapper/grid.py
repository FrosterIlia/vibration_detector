def generate_snake_grid(min_x, min_y, max_x, max_y, points_per_axis):
    if not isinstance(points_per_axis, int) or points_per_axis < 2:
        raise ValueError("points_per_axis must be an integer >= 2")
    if min_x >= max_x:
        raise ValueError("min_x must be less than max_x")
    if min_y >= max_y:
        raise ValueError("min_y must be less than max_y")

    n = points_per_axis - 1
    x_step = (max_x - min_x) / n
    y_step = (max_y - min_y) / n
    xs = [min_x + i * x_step for i in range(n)] + [float(max_x)]

    points = []
    for row in range(points_per_axis):
        y = float(max_y) if row == n else min_y + row * y_step
        row_xs = xs if row % 2 == 0 else xs[::-1]
        for x in row_xs:
            points.append((x, y))
    return points


class ScanGrid:
    def __init__(self, config):
        stepper_x = config.getsection('stepper_x')
        stepper_y = config.getsection('stepper_y')
        self.min_x = stepper_x.getfloat('position_min', 0.)
        self.max_x = stepper_x.getfloat('position_max')
        self.min_y = stepper_y.getfloat('position_min', 0.)
        self.max_y = stepper_y.getfloat('position_max')
        self.points_per_axis = config.getint('points_per_axis', 5, minval=2)
        try:
            self.points = generate_snake_grid(
                self.min_x, self.min_y, self.max_x, self.max_y,
                self.points_per_axis)
        except ValueError as e:
            raise config.error(f"resonance_mapper: {e}")

    def get_points(self):
        return list(self.points)
