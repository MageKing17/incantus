from pydispatch import dispatcher
from characteristics import characteristic

class MtGObject(object):
    #Universal dispatcher
    # this class is for all objects that can send and receive signals
    Any = dispatcher.Any
    #_lock = False
    #_holding = False
    def send(self, event, *args, **named):
        #send event to dispatcher
        dispatcher.send(event, self, *args, **named)
        #if not MtGObject._lock: dispatcher.send(event, self, *args, **named)
        #else: MtGObject._holding.append(lambda: dispatcher.send(event, self, *args, **named))
    def register(self, callback, event, sender=dispatcher.Any, weak=True, expiry=-1):
        # register to receive events
        # if expiry == -1, then it is continuous, otherwise number is the number of times
        # that the callback is processed
        # XXX Major python problem - each callback must be a separate function (or wrapped in a lambda)
        # which makes it hard to disconnect it
        dispatcher.connect(callback, signal=event, sender=sender,weak=weak,expiry=expiry)
    def unregister(self, callback, event, sender=dispatcher.Any, weak=True):
        dispatcher.disconnect(callback, signal=event, sender=sender, weak=weak)
    #@staticmethod
    #def lock():
    #    MtGObject._lock = True
    #    MtGObject._holding = []
    #@staticmethod
    #def release():
    #    MtGObject._lock = False
    #    # Call the sends that were held
    #    for func in MtGObject._holding: func()

class GameObject(MtGObject):
    #__slots__ = ["name", "cost", "color", "type", "subtypes", "supertypes", "owner", "controller", "zone", "out_play_role", "in_play_role", "_current_role"]
    def __init__(self, owner):
        self.owner = owner
        self.controller = owner

        # characteristics
        self.name = None
        self.cost = None
        self.zone = None

        # The next four are characteristics that can be affected by other spells
        self.color = characteristic([])
        self.type = characteristic([])
        self.subtypes = characteristic([])  # Only creatures seem to have subtypes, despite the rules (maybe not 10e)
        self.supertype = characteristic([])

        self.out_play_role = None
        self.in_play_role = None

        self._current_role = None
        self._last_known_role = None
    def owner():
        doc = "The owner of this card - only set once when the card is created"
        def fget(self):
            return self._owner
        return locals()
    #owner = property(**owner())
    def current_role():
        doc = "The current role for this card. Either a Spell (when in hand, library, graveyard or out of game), Spell, (stack) or Permanent (in play)"
        def fget(self):
            return self._current_role
        def fset(self, role):
            # Leaving play
            if role == self.out_play_role and self._current_role != self.out_play_role:
                #  Keep a copy around in case any spells need it
                self._last_known_role = self._current_role
                self._current_role.leavingPlay()
            # Staying in play
            if role == self.in_play_role and self._current_role.__class__ == self.in_play_role.__class__:
                # Do nothing - when we change controllers
                return
            # Make a copy of the role, so that there's no memory whenever we re-enter play
            if role == self.in_play_role: self._current_role = role.copy()
            else: self._current_role = role

            # It is about to enter play - let it know
            if role == self.in_play_role:
                if self._last_known_role: del self._last_known_role
                self._last_known_role = None
                self._current_role.enteringPlay()
        return locals()
    current_role = property(**current_role())
    # I should probably get rid of the getattr call, and make everybody refer to current_role directly
    # But that makes the code so much uglier
    def __getattr__(self, attr):
        if hasattr(self.current_role, attr):
            return getattr(self.current_role,attr)
        else:
            # We are probably out of play - check the last known info
            return getattr(self._last_known_role, attr)
    def __repr__(self):
        return "%s at %s"%(str(self),str(id(self)))

class Card(GameObject):
    def __init__(self, owner):
        super(Card, self).__init__(owner)
        # characteristics
        self.expansion = None
        self.text = None
        self.hidden = False
    def __str__(self):
        return self.name

class GameToken(GameObject):
    def __str__(self):
        return "Token: %s"%self.name
