import copy
from engine.MtGObject import MtGObject
from engine.GameEvent import DealsDamageEvent, DealsDamageToEvent, ReceivesDamageEvent, CardEnteredZone, CardLeftZone, CardEnteringZoneFrom, UpkeepStepEvent, SpellPlayedEvent
from engine.pydispatch.dispatcher import Any, LOWEST_PRIORITY
from EffectsUtilities import robustApply

__all__ = ["Trigger",
           "PhaseTrigger", "YourUpkeepTrigger",
           "SpellPlayedTrigger",
           "DealsDamageTrigger", "DealsDamageToTrigger", "ReceivesDamageTrigger",
           "EnterTrigger", "LeaveTrigger", "EnterFromTrigger",
           "all_match", "source_match", "sender_match", "attached_match", "controller_match"]

all_match = lambda *args: True
source_match = lambda source, card: source == card
sender_match = lambda source, sender: source == sender
attached_match = lambda source, card: source.attached_to == card
controller_match = lambda source, player: source.controller == player

class Trigger(MtGObject):
    def __init__(self, event=None, condition=None, sender=None):
        self.trigger_event = event
        self.trigger_sender = sender
        self.activated = False
        if condition: self.condition = condition
        else: self.condition = all_match
    def check_expiry(self):
        return (self.expiry == -1 or self.count < self.expiry)
    def setup_trigger(self, source, trigger_function, expiry=-1, priority=LOWEST_PRIORITY, weak=True):
        self.source = source
        self.count = 0
        self.expiry = expiry
        self.trigger_function = trigger_function
        self.weak = weak
        if self.trigger_sender == "source": sender = self.source
        else: sender=Any
        self.register(self.filter, event=self.trigger_event, sender=sender, priority=priority, weak=weak)
        self.activated = True
    def clear_trigger(self):
        if self.activated:
            if self.trigger_sender == "source": sender = self.source
            else: sender=Any
            self.unregister(self.filter, event=self.trigger_event, sender=sender, weak=self.weak)
            self.activated = False
    def filter(self, sender, **keys):
        keys["source"] = self.source
        keys["sender"] = sender
        if self.check_expiry() and robustApply(self.condition, **keys):
            robustApply(self.trigger_function, **keys)
            self.count += 1
    def __str__(self): return self.__class__.__name__
    def copy(self):
        return copy.copy(self)

class PhaseTrigger(Trigger):
    def filter(self, sender, player):
        keys = {'player': player, 'source': self.source}
        if self.check_expiry() and robustApply(self.condition, **keys):
            robustApply(self.trigger_function, **keys)
            self.count += 1

class YourUpkeepTrigger(PhaseTrigger):
    def __init__(self):
        super(PhaseTrigger, self).__init__(UpkeepStepEvent(), condition=controller_match)

class SpellPlayedTrigger(Trigger):
    def __init__(self, condition=None, sender=None):
        super(SpellPlayedTrigger, self).__init__(event=SpellPlayedEvent(), condition=condition, sender=sender)


class DealsDamageTrigger(Trigger):
    def __init__(self, condition=None, sender=None):
        super(DealsDamageTrigger, self).__init__(event=DealsDamageEvent(), condition=condition, sender=sender)
class DealsDamageToTrigger(Trigger):
    def __init__(self, condition=None, sender=None):
        super(DealsDamageToTrigger, self).__init__(event=DealsDamageToEvent(), condition=condition, sender=sender)
class ReceivesDamageTrigger(Trigger):
    def __init__(self, condition=None, sender=None):
        super(ReceivesDamageTrigger, self).__init__(event=ReceivesDamageEvent(), condition=condition, sender=sender)

# The next triggers are for events that pertain to cards but aren't sent by the card itself (ie zone changes, spells of abilities of cards)

class MoveTrigger(Trigger):
    def __init__(self, event, zone, condition=None, player="you"):
        super(MoveTrigger, self).__init__(event=event, condition=condition)
        self.zone = zone
        self.player = player
    def check_player(self, card):
        card_cntrl = card.controller  # Out of battlefield defaults to owner
        cntrl = self.source.controller

        return ((self.player == "you" and card_cntrl == cntrl) or
                (self.player == "opponent" and card_cntrl in cntrl.opponents) or
                (self.player == "any"))
    def filter(self, sender, card):
        keys = {"sender": sender, "source": self.source, "card":card}
        if (self.zone == str(sender) and
            self.check_player(card) and
            robustApply(self.condition, **keys) and
            self.check_expiry()):
            robustApply(self.trigger_function, **keys)
            self.count += 1

class EnterTrigger(MoveTrigger):
    def __init__(self, zone, condition=None, player="you"):
        super(EnterTrigger,self).__init__(event=CardEnteredZone(), zone=zone, condition=condition, player=player)
class LeaveTrigger(MoveTrigger):
    def __init__(self, zone, condition=None, player="you"):
        super(LeaveTrigger,self).__init__(event=CardLeftZone(), zone=zone, condition=condition, player=player)

class EnterFromTrigger(MoveTrigger):
    def __init__(self, to_zone, from_zone, condition=None, player="you"):
        super(EnterFromTrigger,self).__init__(event=CardEnteringZoneFrom(), zone=from_zone, condition=condition, player=player)
        self.to_zone = to_zone
    def filter(self, sender, from_zone, oldcard, newcard):
        keys = {"source": self.source, "card": oldcard, "newcard": newcard}
        if ((str(sender) == self.to_zone and str(from_zone) == self.zone) and
             self.check_player(oldcard) and
             robustApply(self.condition, **keys) and
             self.check_expiry()):
            robustApply(self.trigger_function, **keys)
            self.count += 1
