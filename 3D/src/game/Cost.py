from GameEvent import SacrificeEvent, CounterAddedEvent, CounterRemovedEvent, InvalidTargetEvent
from LazyInt import LazyInt
import Mana
from Match import isCard

class Cost(object):
    def precompute(self, card, player): return True
    def compute(self, card, player): return True
    def pay(self, card, player): pass
    def __add__(self, other):
        if isinstance(other, str): return MultipleCosts([self,ManaCost(other)])
        elif isinstance(other, MultipleCosts): return MultipleCosts([self]+other.costs)
        elif isinstance(other, Cost): return MultipleCosts([self, other])
    def __eq__(self, other):
        return False
    def __str__(self):
        return ''

class NoCost(object):
    def precompute(self, card, player): return False
    def compute(self, card, player): return False
    def __eq__(self, other): return isinstance(other, NoCost)
    def __str__(self): return ''
    def converted_cost(self): return 0

class MultipleCosts(Cost):
    def __init__(self, costs):
        super(MultipleCosts,self).__init__()
        self.costs = self.consolidate(costs)
    def consolidate(self, costs):
        # This combines all mana costs
        newcost = []
        manacost = []
        for c in costs:
            if type(c) == str: manacost.append(ManaCost(c))
            elif isinstance(c,ManaCost): manacost.append(c)
            else: newcost.append(c)
        # If this first ManaCost has an X, the following reduce will ensure that we keep it as the final ManaCost object
        if manacost: costs = [reduce(lambda x,y: x+y, manacost)]+newcost
        return costs
    def precompute(self, card, player):
        for cost in self.costs:
            if not cost.precompute(card, player): return False
        return True
    def compute(self, card, player):
        for cost in self.costs:
            if not cost.compute(card, player): return False
        return True
    def pay(self, card, player):
        for cost in self.costs:
            cost.pay(card, player)
    def __iadd__(self, other):
        if isinstance(other, str): self.costs.append(ManaCost(other))
        elif isinstance(other, MultipleCosts): self.costs.extend(other.costs)
        elif isinstance(other, Cost): self.costs.append(other)
        return self
    def __add__(self, other):
        if isinstance(other, str): return MultipleCosts(self.costs+[ManaCost(other)])
        elif isinstance(other, MultipleCosts): return MultipleCosts(self.costs+other.costs)
        elif isinstance(other, Cost): return MultipleCosts(self.costs+[other])
    def __str__(self):
        return ','.join([str(c) for c in self.costs])

class ManaCost(Cost):
    def cost():
        def fget(self):
            return str(self._mana_amt)
        return locals()
    cost = property(**cost())
    def __init__(self, cost):
        super(ManaCost,self).__init__()
        self._mana_amt = cost
        self._X = 0
        self.X = LazyInt(self._get_X, finalize=True)
    def _get_X(self): return self._X
    def precompute(self, card, player):
        mp = player.manapool
        cost = mp.convert_mana_string(self.cost)
        self.payment = "0"
        self._X = 0
        if mp.checkX(self.cost):
            self._X = player.getX()
            cost[-1] += self._X
        self.final_cost = cost
        return self._X >= 0
    def compute(self, card, player):
        # XXX This is where I should check if the player has enough mana and the player should be
        # able to generate more mana
        mp = player.manapool
        cost = self.final_cost
        for i, val in enumerate(cost):
            if val < 0: cost[i] = 0
        while True:
            required = mp.checkRequired(cost)
            if required == '0': return True
            if not player.getMoreMana(required): return False
    def pay(self, card, player):
        mp = player.manapool
        # Now I have enough mana - how do I distribute it?
        payment = mp.distributeMana(self.final_cost)
        # Consolidate any colorless in the final cost
        if not payment: payment = player.getManaChoice(required=mp.convert_to_mana_string(self.final_cost))
        mp.spend(payment)
        self.payment = payment
    def hasX(self):
        return 'X' in self.cost
    def converted_cost(self):
        return Mana.converted_mana_cost(self.cost)
    def __eq__(self, other):
        if isinstance(other, str): return Mana.compareMana(self.cost, other)
        elif isinstance(other, ManaCost): return Mana.compareMana(self.cost, other.cost)
    def __add__(self, other):
        if isinstance(other, str): return ManaCost(Mana.combine_mana_strings(self.cost, other))
        elif isinstance(other, ManaCost): return ManaCost(Mana.combine_mana_strings(self.cost, other.cost))
        elif isinstance(other, MultipleCosts): return MultipleCosts([self, other.costs])
        elif isinstance(other, Cost): return MultipleCosts([self, other])
    def __str__(self):
        coststr = self.cost
        if self.hasX(): coststr += ",(X=%d)"%self.X
        return coststr
    def __cmp__(self, value):
        return cmp(Mana.converted_mana_cost(self.cost), value)

class TapCost(Cost):
    def __init__(self, number=1, cardtype=None):
        super(TapCost,self).__init__()
        self.cardtype = cardtype
        self.number = number
    def precompute(self, card, player):
        location = player.play
        if self.cardtype == None: return card.current_role.canTap()
        else: return len(location.get(self.cardtype)) >= self.number
    def compute(self, card, player):
        self.targets = []
        # Tap myself
        if self.cardtype == None:
            self.targets.append(card)
        # otherwise see if there are enough targets for tapping
        else:
            location = player.play
            prompt = "Select %d %s(s) for tapping"%(self.number-len(self.targets), self.cardtype)
            while True:
                target = player.getTarget(self.cardtype, zone=location, required=False, prompt=prompt)
                if target == False: return False
                if target in self.targets:
                    prompt = "Target already selected - select again"
                    player.send(InvalidTargetEvent(), target=target)
                elif target.tapped:
                    prompt = "Target already tapped - select again"
                    player.send(InvalidTargetEvent(), target=target)
                elif not target.canBeTapped():
                    prompt = "Target cannot be tapped - select again"
                    player.send(InvalidTargetEvent(), target=target)
                else:
                    self.targets.append(target)
                    prompt = "Select %d %s(s) for tapping"%(self.number-len(self.targets), self.cardtype)
                if len(self.targets) == self.number: break
        return True
    def pay(self, card, player):
        for target in self.targets: target.tap()
    def __str__(self):
        if self.cardtype: who = " %s"%self.cardtype
        else: who = ""
        return 'T%s'%who

class SacrificeCost(Cost):
    def __init__(self, cardtype=None, number=1):
        super(SacrificeCost,self).__init__()
        self.cardtype = cardtype
        self.number = number
    def precompute(self, card, player):
        location = player.play
        if self.cardtype == None: return True
        else: return len(location.get(self.cardtype)) >= self.number
    def compute(self, card, player):
        self.targets = []
        if self.cardtype == None:
            # Sacrifice myself
            self.targets.append(card)
        else:
            location = player.play
            prompt = "Select %d %s(s) for sacrifice"%(self.number-len(self.targets), self.cardtype)
            while True:
                target = player.getTarget(self.cardtype, zone=location, required=False, prompt=prompt)
                if target == False: return False
                if target in self.targets:
                    prompt = "Target already selected - select again"
                    player.send(InvalidTargetEvent(), target=target)
                else:
                    self.targets.append(target)
                    prompt = "Select %d %s(s) for sacrifice"%(self.number-len(self.targets), self.cardtype)
                if len(self.targets) == self.number: break
        return True
    def pay(self, card, player):
        location = player.play
        for target in self.targets:
            player.moveCard(target, location, target.owner.graveyard)
            #player.send(Sacrifice())
    def __str__(self):
        return 'Sacrifice'

class ChangeZoneCost(Cost):
    def __init__(self, from_zone, to_zone, number=1, cardtype=None):
        super(ChangeZoneCost,self).__init__()
        self.cardtype = cardtype
        self.number = number
        self.from_zone = from_zone
        self.to_zone = to_zone
    def precompute(self, card, player):
        from_zone = getattr(player, self.from_zone)
        if self.cardtype == None: return True
        else: return len(from_zone.get(self.cardtype)) >= self.number
    def compute(self, card, player):
        self.targets = []
        if self.cardtype == None:
            self.targets.append(card)
        else:
            from_zone = getattr(player, self.from_zone)
            prompt = "Select %d %s(s) to %s"%(self.number-len(self.targets), self.cardtype, self.action_txt%'')
            while True:
                target = player.getTarget(self.cardtype, zone=from_zone, required=False, prompt=prompt)
                if target == False: return False
                if target in self.targets:
                    prompt = "%s already selected - select again"%self.cardtype
                    player.send(InvalidTargetEvent(), target=target)
                else:
                    self.targets.append(target)
                    prompt = "Select %d %s(s) to %s"%(self.number-len(self.targets), self.cardtype, self.action_txt%'')
                if len(self.targets) == self.number: break
        return True
    def pay(self, card, player):
        for target in self.targets:
            to_zone = getattr(target.owner, self.to_zone)
            player.moveCard(target, target.zone, to_zone)
    def __str__(self):
        if self.cardtype: txt = str(self.cardtype)
        else: txt = ''
        return self.action_txt.title()%txt


class ReturnToHandCost(ChangeZoneCost):
    def __init__(self, number=1, cardtype=None):
        super(ReturnToHandCost,self).__init__(from_zone="play", to_zone="hand", number=number, cardtype=cardtype)
        self.action_txt = "return %s to hand"

class RemoveFromHandCost(ChangeZoneCost):
    def __init__(self, number=1, cardtype=None):
        super(RemoveFromHandCost,self).__init__(from_zone="hand", to_zone="removed", number=number, cardtype=cardtype)
        self.action_txt = "remove %s from hand"

class RemoveFromGraveyardCost(ChangeZoneCost):
    def __init__(self, number=1, cardtype=None):
        super(RemoveFromHandCost,self).__init__(from_zone="graveyard", to_zone="removed", number=number, cardtype=cardtype)
        self.action_txt = "remove %s from graveyard"

class CounterCost(Cost):
    def __init__(self, counter_type, number=1):
        self.counter_type = counter_type
        self.number = number
    def compute(self, card, player):
        self.counters = [counter for counter in card.counters if counter == self.counter_type]
        return len(self.counters) >= self.number
    def pay(self, card, player):
        for i in range(self.number):
            card.counters.remove(self.counters[i])
            card.send(CounterRemovedEvent(), counter=self.counters[i])
    def __str__(self):
        return "%d %s counter(s)"%(self.number, self.counter_type)

class AddCounterCost(Cost):
    def __init__(self, counter, number=1):
        self.counter = counter
        self.number = number
    def compute(self, card, player):
        self.counters = [self.counter.copy() for i in range(self.number)]
        return True
    def pay(self, card, player):
        card.counters.extend(self.counters)
        for i in range(self.number):
            card.send(CounterAddedEvent(), counter=self.counters[i])
    def __str__(self):
        return "Add %d %s counter(s)"%(self.number, self.counter)

class ConditionalCost(Cost):
    def __init__(self, orig_cost, new_cost, func):
        if type(orig_cost) == str: orig_cost = ManaCost(orig_cost)
        if type(new_cost) == str: new_cost = ManaCost(new_cost)
        self.orig_cost = orig_cost
        self.new_cost = new_cost
        self.cost = self.orig_cost
        self.func = func
    def precompute(self, card, player):
        if self.func(card, player): self.cost = self.new_cost
        return self.cost.precompute(card, player)
    def compute(self, card, player):
        return self.cost.compute(card, player)
    def pay(self, card, player):
        self.cost.pay(card, player)
    def __str__(self):
        return str(self.cost)

class LifeCost(Cost):
    def __init__(self, amt):
        self.amt = amt
    def precompute(self, card, player):
        return player.life - self.amt > 0
    def pay(self, card, player):
        player.life -= self.amt
    def __str__(self):
        return "Pay %d life"%self.amt

class RevealCost(Cost):
    def __init__(self, number=1, cardtype=isCard):
        self.number = number
        self.cardtype = cardtype
    def precompute(self, card, player):
        return len(player.hand.get(self.cardtype)) >= self.number
    def compute(self, card, player):
        self.reveals = []
        if self.number > 1: a='s'
        else: a = ''
        num = 0
        prompt = "Select %s card%s to reveal: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
        while num < self.number:
            card = player.getTarget(self.cardtype, zone=player.hand, required=False,prompt=prompt)
            if not card: return False
            if not card in self.reveals:
                self.reveals.append(card)
                num += 1
                prompt = "Select %s card%s to reveal: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
            else:
                prompt = "Card already selected. Select %s card%s to reveal: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
        return True
    def pay(self, card, player):
        player.opponent.revealCard(self.reveals)
    def __str__(self):
        txt = "%d %s"%(self.number, str(self.cardtype))
        if self.number > 1: txt += 's'
        return "Reveal %s"%txt

class DiscardCost(Cost):
    def __init__(self, number=1, cardtype=None):
        self.number = number
        self.cardtype = cardtype
    def precompute(self, card, player):
        if self.cardtype: return len(player.hand.get(self.cardtype)) >= self.number
        else: return True
    def compute(self, card, player):
        self.discards = []
        if self.number == -1:
            # Discard entire hand
            self.discards.extend([c for c in player.hand])
        elif not self.cardtype:
            # Discard this card
            self.discards = [card]
        else:
            if self.number > 1: a='s'
            else: a = ''
            num = 0
            prompt = "Select %s card%s to discard: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
            while num < self.number:
                card = player.getTarget(self.cardtype, zone=player.hand,required=False,prompt=prompt)
                if not card: return False
                if not card in self.discards:
                    self.discards.append(card)
                    num += 1
                    prompt = "Select %s card%s to discard: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
                else:
                    prompt = "Card already selected. Select %s card%s to discard: %d left of %d"%(self.cardtype, a, self.number-num,self.number)
        return True
    def pay(self, card, player):
        for c in self.discards:
            player.discard(c)
    def __str__(self):
        if self.cardtype:
            txt = "%d %s"%(self.number, str(self.cardtype))
            if self.number > 1: txt += 's'
        else: txt = 'this card'
        return "Discard %s"%txt

class LoyaltyCost(Cost):
    def __init__(self, number=0):
        self.number = number
    def compute(self, card, player):
        from Ability.Counters import Counter
        if self.number < 0:
            number = -self.number
            self.counters = [counter for counter in card.counters if counter == "loyalty"][:number]
            return len(self.counters) >= number
        else:
            self.counters = [Counter("loyalty") for i in range(self.number)]
            return True
    def pay(self, card, player):
        if self.number < 0: func, event = card.counters.remove, CounterRemovedEvent
        else: func, event = card.counters.append, CounterAddedEvent
        for counter in self.counters:
            func(counter)
            card.send(event(), counter=counter)
    def __str__(self):
        return "%d loyalty"%(self.number)

class SpecialCost(Cost):
    def precompute(self, card, player):
        return self.cost.precompute(card, player)
    def compute(self, card, player):
        return self.cost.compute(card, player)
    def pay(self, card, player):
        self.cost.pay(card, player)
    def __str__(self):
        return str(self.cost)

class ChoiceCost(SpecialCost):
    def __init__(self, *costs):
        super(ChoiceCost,self).__init__()
        self.choice_costs = costs
        self.reset()
    def reset(self): self.cost = None
    def precompute(self, card, player):
        self.cost = player.getSelection(self.choice_costs, 1, prompt="Select additional cost")
        return super(ChoiceCost, self).precompute(card, player)
    def __str__(self):
        return "Choose between %s"%' or '.join([str(c) for c in self.choice_costs])

class EvokeCost(SpecialCost):
    def __init__(self, orig_cost, evoke_cost):
        if type(orig_cost) == str: orig_cost = ManaCost(orig_cost)
        if type(evoke_cost) == str: evoke_cost = ManaCost(evoke_cost)
        self.orig_cost = orig_cost
        self.evoke_cost = evoke_cost
        self.reset()
    def reset(self):
        self.evoked = False
        self.cost = self.orig_cost
    def precompute(self, card, player):
        self.evoked = player.getIntention("Pay evoke cost?", "...pay evoke cost?")
        if self.evoked: self.cost = self.evoke_cost
        return super(EvokeCost, self).precompute(card, player)

class ProwlCost(SpecialCost):
    def __init__(self, orig_cost, prowl_cost):
        if type(orig_cost) == str: orig_cost = ManaCost(orig_cost)
        if type(prowl_cost) == str: prowl_cost = ManaCost(prowl_cost)
        self.orig_cost = orig_cost
        self.prowl_cost = prowl_cost
        self.reset()
    def reset(self):
        self.prowled = False
        self.can_prowl = False
        self.cost = self.orig_cost
    def precompute(self, card, player):
        if self.can_prowl:
            self.prowled = player.getIntention("Pay prowl cost?", "...pay prowl cost?")
            if self.prowled: self.cost = self.prowl_cost
        return super(ProwlCost, self).precompute(card, player)
