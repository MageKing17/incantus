from engine.pydispatch import dispatcher
from engine.pydispatch.robustapply import function
from engine.GameEvent import CleanupEvent
from engine.stacked_function import global_override, override, replace, logical_and, logical_or, do_all

no_condition = None

def do(func, event, condition=lambda *args: True):
    def wrap_(**kw):
        if robustApply(condition, **kw):
            func()
    dispatcher.connect(wrap_, signal=event, weak=False)
    func.expire = lambda: dispatcher.disconnect(wrap_, signal=event, weak=False)

def do_when(func, event, condition=lambda *args: True):
    def wrap_(**kw):
        if robustApply(condition, **kw):
            func()
            dispatcher.disconnect(wrap_, signal=event, weak=False)
    dispatcher.connect(wrap_, signal=event, weak=False)

do_until = do_when

def delay(source, delayed_trigger):
    delayed_trigger.enable(source)
    def expire():
        delayed_trigger.disable()
        #del delayed_trigger  # if I delete this, it seems to get garbage collected when it's first set up
    return expire

def combine(*restores):
    if len(restores) == 1: expire = restores[0]
    else:
        def expire():
            for restore in restores: restore()
    return expire

def until_end_of_turn(*restores):
    dispatcher.connect(combine(*restores), signal=CleanupEvent(), weak=False, expiry=1)

def keyword_action(func):
    from engine.Player import Player
    setattr(Player, func.__name__, func)

def permanent_method(func):
    from engine.CardRoles import Permanent
    setattr(Permanent, func.__name__, func)

do_override = override
do_replace = replace

def override_effect(func_name, func, combiner=logical_and):
    def effects(target):
        yield do_override(target, func_name, func, combiner=combiner)
    return effects

def robustApply(receiver, **named):
    """Call receiver with arguments and an appropriate subset of named
    """
    receiver, codeObject, startIndex = function(receiver)
    acceptable = codeObject.co_varnames[startIndex:codeObject.co_argcount]
    if not (codeObject.co_flags & 8):
        # fc does not have a **kwds type parameter, therefore
        # remove unacceptable arguments.
        for arg in named.keys():
            if arg not in acceptable:
                del named[arg]
    return receiver(**named)
