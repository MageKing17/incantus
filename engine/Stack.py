import weakref
from GameObjects import GameObject
from Zone import Zone
from GameEvent import AbilityPlacedOnStack, AbilityRemovedFromStack

class Stack(Zone):
    name = "stack"
    def __init__(self, game):
        self._abilities = []
        self.game = weakref.proxy(game)
        self.pending_triggered =[]
        super(Stack, self).__init__()
    def setup_new_role(self, card):
        cardtmpl = GameObject._cardmap[card.key]
        return cardtmpl.new_role(cardtmpl.stack_role)
    def add_triggered(self, ability, source):
        self.pending_triggered.append((ability, source))
    def process_triggered(self):
        # Check if there are any triggered abilities waiting
        if len(self.pending_triggered) > 0:
            players = self.game.players
            # group all triggered abilities by player
            triggered_sets = dict([(player, []) for player in players])
            for ability, source in self.pending_triggered:
                player = source.controller
                triggered_sets[player].append(ability)
            # Now ask the player to order them if there are more than one
            for player in players:
                triggered = triggered_sets[player]
                if len(triggered) > 1:
                    triggered = player.make_selection(triggered, -1, prompt="Drag to reorder triggered abilities(Top ability resolves first)")
                # Now reorder
                for ability in triggered: ability.announce(source, player)
            self.pending_triggered[:] = []
            return True
        else: return False
    def push(self, ability):
        self._abilities.append(ability)
        self.send(AbilityPlacedOnStack(), ability=ability)
    def resolve(self):
        ability = self._abilities.pop()
        ability.resolve()
        self.send(AbilityRemovedFromStack(), ability=ability)
    def counter(self, ability):
        self._abilities.remove(ability)
        self.send(AbilityRemovedFromStack(), ability=ability)
    def empty(self): return len(self._abilities) == 0
    def __contains__(self, ability): return ability in self._abilities
    def index(self, ability): return self._abilities.index(ability)
    def __getitem__(self, i): return self._abilities[i]
