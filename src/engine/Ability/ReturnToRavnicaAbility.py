from ActivatedAbility import ActivatedAbility
from EffectsUtilities import do_until, combine, do_override
from engine.GameEvent import NewTurnEvent
from engine.Player import keyword_action
from Counters import PowerToughnessCounter
from CiPAbility import CiP, CiPAbility, no_before
from StaticAbility import ConditionalStaticAbility
from ActivatedAbility import ActivatedAbility
from Target import Target
from Cost import ExileFromGraveyardCost
from Limit import sorcery_limit

__all__ = ['unleash', 'scavenge']

# Done as a keyword action because we need to know which player's turn we're waiting for.
@keyword_action
def detain(controller, card):
    do_until(combine(do_override(card, "canAttack", lambda self: False), do_override(card, "canBlock", lambda self: False), do_override(ActivatedAbility, "playable", lambda self: not self.source == card)), NewTurnEvent(), lambda player: player == controller)

def unleash():
    def during(self):
        '''You may have ~ enter the battlefield with a +1/+1 counter on it.'''
        if self.controller.you_may("have %s enter the battlefield with a +1/+1 counter on it"%self.name): self.add_counters(PowerToughnessCounter(1, 1))
    def effects_1(source):
        yield CiP(source, during, no_before, txt='')
    unleash_1 = CiPAbility(effects_1, keyword="unleash")
    def effects_2(source):
        yield do_override(source, "canBlock", lambda self: False)
    unleash_2 = ConditionalStaticAbility(effects_2, lambda source: source.num_counters("+1+1") > 0, zone="battlefield")
    return unleash_1, unleash_2

def scavenge(cost):
    def effects(controller, source):
        yield cost + ExileFromGraveyardCost()
        yield Target(isCreature)
        target.add_counters(PowerToughnessCounter(1, 1), source.power)
        yield
    return ActivatedAbility(effects, sorcery_limit, zone="graveyard", txt="Scavenge %s"%cost, keyword="scavenge")

@keyword_action
def populate(player):
    selected = player.choose_from_zone(zone="battlefield", cardtype=isToken.with_condition(lambda t: t.types == Creature), action="populate")
    if selected:
        for token in player.make_tokens({}):
            token.clone(selected)
            def modifyNewRole(self, new, zone):
                if str(zone) == "battlefield": new.clone(selected)
            override(token, "modifyNewRole", modifyNewRole)
            token.move_to("battlefield")
