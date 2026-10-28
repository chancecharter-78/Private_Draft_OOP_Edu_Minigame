"""A small logic-programming engine written in pure Python.

It supports facts, rules (Horn clauses), unification, backtracking
queries, arithmetic comparison and negation as failure. Programs are
written in a Prolog-style syntax and parsed by ``KnowledgeBase.consult``.
No Streamlit and no SQL are used here (Model layer rules).
"""
from __future__ import annotations

import operator
import re
from typing import Any, Iterator, NamedTuple


class LogicError(Exception):
    """Raised for syntax errors, unknown predicates and bad arithmetic."""


class Var:
    """A logic variable. Identity (not the name) decides equality."""

    __slots__ = ("name",)

    def __init__(self, name: str = "_"):
        self.name = name

    def __repr__(self) -> str:
        return f"Var({self.name})"


class Term(NamedTuple):
    """A compound term such as combo_tier(12, 1.35)."""

    functor: str
    args: tuple


class Clause(NamedTuple):
    """A fact (empty body) or a rule: head :- body1, body2, ..."""

    head: Term
    body: tuple


_COMPARISONS = {
    ">=": operator.ge,
    "=<": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "=:=": operator.eq,
    "=\\=": operator.ne,
}
_ARITHMETIC = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}
MAX_DEPTH = 200


def walk(term: Any, subst: dict) -> Any:
    while isinstance(term, Var) and term in subst:
        term = subst[term]
    return term


def resolve(term: Any, subst: dict) -> Any:
    term = walk(term, subst)
    if isinstance(term, Term):
        return Term(
            term.functor,
            tuple(resolve(arg, subst) for arg in term.args),
        )
    return term


def unify(a: Any, b: Any, subst: dict) -> dict | None:
    """Return an extended substitution, or None when a and b clash."""
    a, b = walk(a, subst), walk(b, subst)
    if a is b:
        return subst
    if isinstance(a, Var):
        return {**subst, a: b}
    if isinstance(b, Var):
        return {**subst, b: a}
    if isinstance(a, Term) and isinstance(b, Term):
        if a.functor != b.functor or len(a.args) != len(b.args):
            return None
        for left, right in zip(a.args, b.args):
            subst = unify(left, right, subst)
            if subst is None:
                return None
        return subst
    if isinstance(a, Term) or isinstance(b, Term):
        return None
    if type(a) is type(b) and a == b:
        return subst
    return None


def _evaluate(expr: Any, subst: dict) -> Any:
    expr = walk(expr, subst)
    if isinstance(expr, Var):
        raise LogicError("unbound variable in an arithmetic expression")
    if isinstance(expr, Term):
        function = _ARITHMETIC.get(expr.functor)
        if function is None or len(expr.args) != 2:
            raise LogicError(f"not an arithmetic term: {expr.functor}")
        return function(
            _evaluate(expr.args[0], subst),
            _evaluate(expr.args[1], subst),
        )
    return expr


def _rename(term: Any, mapping: dict) -> Any:
    """Give a clause fresh variables each time it is used."""
    if isinstance(term, Var):
        if term not in mapping:
            mapping[term] = Var(term.name)
        return mapping[term]
    if isinstance(term, Term):
        return Term(
            term.functor,
            tuple(_rename(arg, mapping) for arg in term.args),
        )
    return term


_TOKEN = re.compile(
    r"""
    (?:\s+|%[^\n]*)
  | (?P<num>\d+\.\d+|\d+)
  | (?P<var>[A-Z_][A-Za-z0-9_]*)
  | (?P<atom>[a-z][A-Za-z0-9_]*)
  | (?P<op>:-|\\\+|>=|=<|=:=|=\\=|[<>(),.+\-*/])
    """,
    re.VERBOSE,
)


def _tokenise(text: str) -> list[tuple[str, str]]:
    tokens, position = [], 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise LogicError(f"unexpected character {text[position]!r}")
        position = match.end()
        if match.lastgroup is not None:
            tokens.append((match.lastgroup, match.group()))
    return tokens


class _Parser:
    def __init__(self, text: str):
        self._tokens = _tokenise(text)
        self._pos = 0
        self._vars: dict[str, Var] = {}

    def _peek(self) -> tuple[str | None, str | None]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None, None

    def _next(self) -> tuple[str | None, str | None]:
        token = self._peek()
        self._pos += 1
        return token

    def _expect(self, text: str) -> None:
        found = self._next()[1]
        if found != text:
            raise LogicError(f"expected {text!r} but found {found!r}")

    def clauses(self) -> list[Clause]:
        result = []
        while self._peek()[0] is not None:
            self._vars = {}
            head = self._as_goal(self._primary())
            body = []
            if self._peek()[1] == ":-":
                self._next()
                body.append(self._goal())
                while self._peek()[1] == ",":
                    self._next()
                    body.append(self._goal())
            self._expect(".")
            result.append(Clause(head, tuple(body)))
        return result

    def _goal(self) -> Term:
        if self._peek()[1] == "\\+":
            self._next()
            return Term("not", (self._goal(),))
        left = self._expr()
        kind, text = self._peek()
        if text in _COMPARISONS or (kind == "atom" and text == "is"):
            self._next()
            return Term(text, (left, self._expr()))
        return self._as_goal(left)

    @staticmethod
    def _as_goal(value: Any) -> Term:
        if isinstance(value, Term):
            return value
        if isinstance(value, str):
            return Term(value, ())
        raise LogicError(f"not a valid goal: {value!r}")

    def _expr(self) -> Any:
        left = self._product()
        while self._peek()[1] in ("+", "-"):
            op = self._next()[1]
            left = Term(op, (left, self._product()))
        return left

    def _product(self) -> Any:
        left = self._primary()
        while self._peek()[1] in ("*", "/"):
            op = self._next()[1]
            left = Term(op, (left, self._primary()))
        return left

    def _primary(self) -> Any:
        kind, text = self._next()
        if kind == "num":
            return float(text) if "." in text else int(text)
        if kind == "var":
            if text == "_":
                return Var("_")
            return self._vars.setdefault(text, Var(text))
        if kind == "atom":
            if self._peek()[1] != "(":
                return text
            self._next()
            args = [self._expr()]
            while self._peek()[1] == ",":
                self._next()
                args.append(self._expr())
            self._expect(")")
            return Term(text, tuple(args))
        if text == "(":
            inner = self._expr()
            self._expect(")")
            return inner
        raise LogicError(f"unexpected token {text!r}")


class KnowledgeBase:
    """Holds facts and rules and answers queries against them."""

    def __init__(self) -> None:
        self._clauses: dict[tuple[str, int], list[Clause]] = {}

    def consult(self, text: str) -> None:
        """Load Prolog-style facts and rules from a string."""
        for clause in _Parser(text).clauses():
            key = (clause.head.functor, len(clause.head.args))
            self._clauses.setdefault(key, []).append(clause)

    def query(self, functor: str, *args: Any) -> Iterator[tuple]:
        """Yield the resolved argument tuple for every solution."""
        goal = Term(functor, tuple(args))
        for subst in self._solve(goal, {}, 0):
            yield tuple(resolve(arg, subst) for arg in args)

    def holds(self, functor: str, *args: Any) -> bool:
        """True when the goal has at least one solution."""
        return next(self.query(functor, *args), None) is not None

    def _solve(self, goal: Term, subst: dict, depth: int) -> Iterator[dict]:
        if depth > MAX_DEPTH:
            raise LogicError("maximum recursion depth exceeded")
        name, arity = goal.functor, len(goal.args)
        if name == "not" and arity == 1:
            if not any(True for _ in self._solve(goal.args[0], subst, depth + 1)):
                yield subst
            return
        if name in _COMPARISONS and arity == 2:
            left = _evaluate(goal.args[0], subst)
            right = _evaluate(goal.args[1], subst)
            if _COMPARISONS[name](left, right):
                yield subst
            return
        if name == "is" and arity == 2:
            result = unify(goal.args[0], _evaluate(goal.args[1], subst), subst)
            if result is not None:
                yield result
            return
        if (name, arity) not in self._clauses:
            raise LogicError(f"unknown predicate {name}/{arity}")
        for clause in self._clauses[(name, arity)]:
            mapping: dict = {}
            head = _rename(clause.head, mapping)
            body = [_rename(item, mapping) for item in clause.body]
            result = unify(goal, head, subst)
            if result is not None:
                yield from self._solve_all(body, result, depth + 1)

    def _solve_all(self, goals: list, subst: dict, depth: int) -> Iterator[dict]:
        if not goals:
            yield subst
            return
        for result in self._solve(goals[0], subst, depth):
            yield from self._solve_all(goals[1:], result, depth)
