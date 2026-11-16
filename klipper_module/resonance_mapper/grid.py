class ScanGrid:
    def __init__(self, min_x, min_y, max_x, max_y, points_per_axis):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self.points_per_axis = points_per_axis
        self.points = self.generate_snake_grid()

    def generate_snake_grid(self):
        if not isinstance(self.points_per_axis, int) or self.points_per_axis < 2:
            raise ValueError("points_per_axis must be an integer >= 2")
        if self.min_x >= self.max_x:
            raise ValueError("min_x must be less than max_x")
        if self.min_y >= self.max_y:
            raise ValueError("min_y must be less than max_y")

        n = self.points_per_axis - 1
        x_step = (self.max_x - self.min_x) / n
        y_step = (self.max_y - self.min_y) / n
        xs = [self.min_x + i * x_step for i in range(n)] + [float(self.max_x)]

        points = []
        for row in range(self.points_per_axis):
            y = float(self.max_y) if row == n else self.min_y + row * y_step
            row_xs = xs if row % 2 == 0 else xs[::-1]
            for x in row_xs:
                points.append((x, y))
        return points

    def get_points(self):
        return list(self.points)
