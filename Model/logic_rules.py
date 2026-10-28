"""Game rules written as logic-programming facts, rules and queries.

The program below is consulted by Model/logic_engine.py. The wrapper
functions turn Python values into queries and return plain Python
values. Callers in the Model layer fall back to their original Python
code whenever LogicEngineError is raised.
"""
from __future__ import annotations

import functools

from Model.logic_engine import KnowledgeBase, Var


class LogicEngineError(RuntimeError):
    """The logic engine could not answer; use the Python fallback."""


PROGRAM = r"""
% ---- Combo tiers: combo_tier(MinimumStreak, Multiplier) ----
combo_tier(12, 1.35).
combo_tier(9, 1.25).
combo_tier(6, 1.15).
combo_tier(3, 1.05).

tier_reached(Streak, Min) :- combo_tier(Min, _), Streak >= Min.
beaten(Streak, Min) :-
    combo_tier(Higher, _), Higher > Min, Streak >= Higher.

combo_multiplier(Streak, Multiplier) :-
    combo_tier(Min, Multiplier), Streak >= Min,
    \+ beaten(Streak, Min).
combo_multiplier(Streak, 1.00) :- \+ tier_reached(Streak, _).

% ---- Inverse query: lowest streak that gives a multiplier ----
multiplier_reached(Multiplier, Tier) :-
    combo_tier(_, Tier), Multiplier >= Tier.
outranked(Multiplier, Tier) :-
    combo_tier(_, Higher), Higher > Tier, Multiplier >= Higher.

streak_for_multiplier(Multiplier, Streak) :-
    combo_tier(Streak, Tier), Multiplier >= Tier,
    \+ outranked(Multiplier, Tier).
streak_for_multiplier(Multiplier, 2) :-
    \+ multiplier_reached(Multiplier, _).

% ---- Review scheduling and servers ----
question_due(no_card, _, _).
question_due(has_card, Due, Now) :- Due =< Now.

server_online(SetCount, DueCount) :- SetCount > 0, DueCount =:= 0.

% ---- Automatic rating from performance (1 Again .. 4 Easy) ----
rating(lost, _, _, 1).
rating(won, Time, Target, 4) :- Time =< Target * 0.5.
rating(won, Time, Target, 3) :-
    \+ Time =< Target * 0.5, Time =< Target.
rating(won, Time, Target, 2) :-
    \+ Time =< Target * 0.5, \+ Time =< Target.
"""


@functools.lru_cache(maxsize=1)
def _knowledge_base() -> KnowledgeBase:
    knowledge_base = KnowledgeBase()
    knowledge_base.consult(PROGRAM)
    return knowledge_base


def _first(functor: str, *args):
    try:
        answer = next(_knowledge_base().query(functor, *args), None)
    except Exception as error:
        raise LogicEngineError(str(error)) from error
    if answer is None:
        raise LogicEngineError(f"no solution for {functor}{args}")
    return answer


def _holds(functor: str, *args) -> bool:
    try:
        return _knowledge_base().holds(functor, *args)
    except Exception as error:
        raise LogicEngineError(str(error)) from error


def combo_multiplier(streak) -> float:
    return _first("combo_multiplier", streak, Var("Multiplier"))[1]


def streak_for_multiplier(multiplier) -> int:
    return _first("streak_for_multiplier", multiplier, Var("Streak"))[1]


def is_due(card, due, now) -> bool:
    kind = "no_card" if card is None else "has_card"
    return _holds("question_due", kind, due, now)


def is_online(question_set_count, due_count) -> bool:
    return _holds("server_online", question_set_count, due_count)


def performance_rating(won, time_taken, target_seconds) -> int:
    if won and target_seconds <= 0:
        raise ValueError("target_seconds must be greater than zero.")
    outcome = "won" if won else "lost"
    return _first(
        "rating", outcome, time_taken, target_seconds, Var("Rating")
    )[3]
