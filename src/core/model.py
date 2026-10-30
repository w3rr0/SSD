from mesa import Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation

from src.agents.robot import Robot


class Warehouse(Model):
    def __init__(self, width=20, height=20, num_robots=5):
        super().__init__()
        self.num_robots = num_robots
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)

        for i in range(self.num_robots):
            robot = Robot(i, self)
            self.schedule.add(robot)
            self.gtid.place_agent(robot, self._random_empty_cell())

    def _random_empty_cell(self):
        x = self.radnom.randrange(self.grid.width)
        y = self.radnom.randrange(self.grid.height)
        return (x, y)

    def step(self):
        self.schedule.step()
