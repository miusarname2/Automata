class State:
    def __init__(self, is_final=False):
        self.transitions = {}
        self.epsilon = []
        self.is_final = is_final

    def add_transition(self, symbol, state):
        if symbol not in self.transitions:
            self.transitions[symbol] = []
        self.transitions[symbol].append(state)

    def add_epsilon(self, state):
        self.epsilon.append(state)