from mesa import Agent


class Robot(Agent):
    def __init__(self, id, model):
        super().__init__(id, model)
        self.battery = 100

    def step(self):
        possible_steps = self.model.grid.get_neighbourood(
            self.pos,
            moore=False,
            include_center=False,
        )

        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)
