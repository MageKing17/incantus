from game.GameObjects import MtGObject
from game.GameEvent import DealsDamageEvent, ReceivesDamageEvent, DealsCombatDamageEvent, ReceivesCombatDamageEvent, CardEnteredZone, CardLeftZone, CardEnteringZone, CardLeavingZone, TimestepEvent
from game.Match import SelfMatch
from game.LazyInt import LazyInt
from game.pydispatch.robustapply import function

def robustApply(receiver, *arguments, **named):
    """Call receiver with arguments and an appropriate subset of named
    """
    receiver, codeObject, startIndex = function( receiver )
    acceptable = codeObject.co_varnames[startIndex:codeObject.co_argcount]
    for name in acceptable:
        if name == "sender":
            named[name] = arguments[0]
            break
        elif not named.has_key(name): break
    else: arguments = ()

    acceptable = codeObject.co_varnames[startIndex+len(arguments):codeObject.co_argcount]
    if not (codeObject.co_flags & 8):
        # fc does not have a **kwds type parameter, therefore
        # remove unacceptable arguments.
        for arg in named.keys():
            if arg not in acceptable:
                del named[arg]
    return receiver(*arguments, **named)

class Trigger(MtGObject):
    def __init__(self, event=None, sender=MtGObject.Any):
        self.trigger_event = event
        self.trigger_sender = sender
        self.activated = False
    def setup_trigger(self, ability, trigger_function, match_condition=None, expiry=-1):
        self.count = 0
        self.expiry = expiry
        self.ability = ability
        self.trigger_function = trigger_function
        if match_condition: self.match_condition = match_condition
        else: self.match_condition = lambda *args: True
        self.register(self.filter, event=self.trigger_event, sender=self.trigger_sender)
        self.activated = True
    def clear_trigger(self, wait=True):
        # This guarantees that all simultaneous events are caught by a registered trigger
        if self.activated:
            unregister = lambda: self.unregister(self.filter, event=self.trigger_event, sender=self.trigger_sender)
            if wait: self.register(unregister, event=TimestepEvent(), weak=False, expiry=1)
            else: unregister()
            self.activated = False
    def filter(self, sender, **keys):
        if robustApply(self.match_condition, sender, **keys) and (self.expiry == -1 or self.count < self.expiry):
            self.sender = sender
            self.__dict__.update(keys)
            self.trigger_function(self)
            self.count += 1

class PlayerTrigger(Trigger):
    def filter(self):
        from game.GameKeeper import Keeper
        player = Keeper.curr_player
        if self.match_condition(player) and (self.expiry == -1 or self.count < self.expiry):
            self.player = player
            self.trigger_function(self)
            self.count += 1

class DealDamageTrigger(Trigger):
    def __init__(self, sender=MtGObject.Any):
        super(DealDamageTrigger, self).__init__(event=DealsDamageEvent(), sender=sender)
class ReceiveDamageTrigger(Trigger):
    def __init__(self, sender=MtGObject.Any):
        super(ReceiveDamageTrigger, self).__init__(event=ReceivesDamageEvent(), sender=sender)
class DealCombatDamageTrigger(Trigger):
    def __init__(self, sender=MtGObject.Any):
        super(DealCombatDamageTrigger, self).__init__(event=DealsCombatDamageEvent(), sender=sender)
class ReceiveCombatDamageTrigger(Trigger):
    def __init__(self, sender=MtGObject.Any):
        super(ReceiveCombatDamageTrigger, self).__init__(event=ReceivesCombatDamageEvent(), sender=sender)

# The next triggers are for events that pertain to cards but aren't sent by the card itself (ie zone changes, spells of abilities of cards)
class CardTrigger(Trigger):
    def filter(self, sender, card):
        if self.match_condition(card) and (self.expiry == -1 or self.count < self.expiry):
            self.sender = sender
            self.matched_card = card
            self.trigger_function(self)
            self.count += 1

class MoveTrigger(CardTrigger):
    def __init__(self, event=None, zone=None, any=False):
        super(MoveTrigger, self).__init__(event=event)
        self.zone = zone
        self.any = any
    def setup_trigger(self, ability, trigger_function, match_condition=None, expiry=-1):
        self.count = 0
        self.expiry = expiry
        self.ability = ability
        self.trigger_function = trigger_function
        if match_condition: self.match_condition = match_condition
        else: self.match_condition = lambda *args: True
        self.events_senders = []
        if self.any:
            self.events_senders.append((self.trigger_event, getattr(ability.card.controller, self.zone)))
            self.events_senders.append((self.trigger_event, getattr(ability.card.controller.opponent, self.zone)))
        else:
            if self.zone == "play": trigger_sender = getattr(ability.card.controller, self.zone)
            else: trigger_sender = getattr(ability.card.owner, self.zone)
            self.events_senders.append((self.trigger_event, trigger_sender))
        for event, sender in self.events_senders:
            self.register(self.filter, event=event, sender=sender)
        self.activated = True
    def clear_trigger(self, wait=True):
        if self.activated:
            # closures are not bound properly in loops, so have to define an external function
            def unregister(event, sender):
                return lambda: self.unregister(self.filter, event=event, sender=sender)
            for event, sender in self.events_senders:
                if wait: self.register(unregister(event, sender), event=TimestepEvent(), weak=False, expiry=1)
                else: self.unregister(self.filter, event=event, sender=sender)
            self.activated = False

class EnterTrigger(MoveTrigger):
    def __init__(self, zone=None, any=False):
        super(EnterTrigger,self).__init__(event=CardEnteredZone(), zone=zone, any=any)
class LeaveTrigger(MoveTrigger):
    def __init__(self, zone=None, any=False):
        super(LeaveTrigger,self).__init__(event=CardLeftZone(), zone=zone, any=any)
class EnteringTrigger(MoveTrigger):
    def __init__(self, zone=None, any=False):
        super(EnteringTrigger,self).__init__(event=CardEnteringZone(), zone=zone, any=any)
class LeavingTrigger(MoveTrigger):
    def __init__(self, zone=None, any=False):
        super(LeavingTrigger,self).__init__(event=CardLeavingZone(), zone=zone, any=any)

class EnterFromTrigger(Trigger):
    def __init__(self, from_zone, to_zone):
        super(EnterFromTrigger,self).__init__(event=None)
        self.from_zone = from_zone
        self.to_zone = to_zone
        # We need to keep track of all zone changes, to make sure that we catch the right sequence of events
        # although only enter events, since we can infer the correct move from a sequence of enter events
    def setup_trigger(self, ability, trigger_function, match_condition=None, expiry=-1):
        self.entering = set()
        self.count = 0
        self.expiry = expiry
        self.ability = ability
        self.trigger_function = trigger_function
        if match_condition: self.match_condition = match_condition
        else: self.match_condition = lambda *args: True
        self.events_senders = [(CardEnteringZone(), self.filter_entering), (CardLeftZone(), self.filter_left)]
        for event, filter in self.events_senders: self.register(filter, event=event)
        self.activated = True
    def clear_trigger(self, wait=True):
        if self.activated:
            # closures are not bound properly in loops, so have to define an external function
            def unregister(event, filter):
                return lambda: self.unregister(filter, event=event)
            for event, filter in self.events_senders:
                if wait: self.register(unregister(event, filter), event=TimestepEvent(), weak=False, expiry=1)
                else: self.unregister(filter, event=event)
            self.activated = False
    def filter_entering(self, sender, card):
        if self.match_condition(card) and str(sender) == self.to_zone:
            self.entering.add(card)
    def filter_left(self, sender, card):
        if card in self.entering:
            self.entering.remove(card)
            if str(sender) == self.from_zone and card in self.entering:
                self.matched_card = card
                if (self.expiry == -1 or self.count < self.expiry): self.trigger_function(self)
                self.count += 1
