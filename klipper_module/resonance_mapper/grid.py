class ScanGrid:
    def __init__(self, min_x, min_y, max_x, max_y, points_per_axis,
                 margin=0.):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self.points_per_axis = points_per_axis
        self.margin = margin
        self.points = self.generate_snake_grid()

    def generate_snake_grid(self):
        if not isinstance(self.points_per_axis, int) or self.points_per_axis < 2:
            raise ValueError("points_per_axis must be an integer >= 2")
        if self.margin < 0:
            raise ValueError("margin must be >= 0")
        min_x = self.min_x + self.margin
        max_x = self.max_x - self.margin
        min_y = self.min_y + self.margin
        max_y = self.max_y - self.margin
        if min_x >= max_x:
            raise ValueError("margin is too large for the X range")
        if min_y >= max_y:
            raise ValueError("margin is too large for the Y range")

        n = self.points_per_axis - 1
        x_step = (max_x - min_x) / n
        y_step = (max_y - min_y) / n
        xs = [min_x + i * x_step for i in range(n)] + [float(max_x)]

        points = []
        for row in range(self.points_per_axis):
            y = float(max_y) if row == n else min_y + row * y_step
            row_xs = xs if row % 2 == 0 else xs[::-1]
            for x in row_xs:
                points.append((x, y))
        return points

    def get_points(self):
        return list(self.points)
