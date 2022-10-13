"""Various context related utilities, including inference and call contexts."""

from contextvars import Context
from lib2to3.pytree import Node
from pprint import pprint
from subprocess import call
from typing import Dict, Optional, Sequence, Tuple


class InferenceContext:
    """Provide context for inference.

    Store already inferred nodes to save time.
    Account for already visited nodes to stop infinite recursion.
    """

    __slots__ = (
        "path",
        "lookupname",
        "callcontext",
        "boundnode",
        "extra_context",
        "_nodes_inferred",
    )

    max_inferred = 100

    def __init__(self, path=None, nodes_inferred=None):
        if nodes_inferred is None:
            self._nodes_inferred = [0]
        else:
            self._nodes_inferred = nodes_inferred
        self.path = path or set()

        self.lookupname = None
        self.callcontext = None
        self.boundnode = None
        self.extra_context = {}

    @property
    def nodes_inferred(self):
        """Number of nodes inferred in this context and all its clones/descendents.

        Wrap inner value in a mutable cell to allow for mutating a class
        variable in the presence of __slots__.
        """
        return self._nodes_inferred[0]

    @nodes_inferred.setter
    def nodes_inferred(self, value):
        self._nodes_inferred[0] = value

    @property
    def inferred(self):
        """Inferred node contexts to their mapped results.

        Currently the key is ``(node, lookupname, callcontext, boundnode)``
        and the value is tuple of the inferred results.
        """
        return _INFERENCE_CACHE

    def push(self, node):
        """Push node into inference path.

        Allows one to see if the given node has already
        been looked at for this inference context.

        Parameters
        ----------
        node : Node
            The given node.

        Returns
        -------
        ret : bool
            True if node is already in context path else False.
        """
        name = self.lookupname
        if (node, name) in self.path:
            return True

        self.path.add((node, name))
        return False

    def clone(self):
        """Clone inference path.

        For example, each side of a binary operation (BinOp)
        starts with the same context but diverge as each side is inferred
        so the InferenceContext will need be cloned.
        """
        # XXX copy lookupname/callcontext ?
        clone = InferenceContext(self.path.copy(), nodes_inferred=self._nodes_inferred)
        clone.callcontext = self.callcontext
        clone.boundnode = self.boundnode
        clone.extra_context = self.extra_context
        return clone

    def __str__(self):
        state = (
            f"{field}={pprint.pformat(getattr(self, field), width=80 - len(field))}"
            for field in self.__slots__
        )
        return "{}({})".format(type(self).__name__, ",\n    ".join(state))


class CallContext:
    """Holds information for a call site."""

    __slots__ = ("args", "keywords", "callee")

    def __init__(self, args, keywords=None, callee=None) -> None:
        self.args = args  # Call positional arguments
        if keywords:
            arg_value_pairs = [(arg.arg, arg.value) for arg in keywords]
        else:
            arg_value_pairs = []
        self.keywords = arg_value_pairs  # Call keyword arguments
        self.callee = callee  # Function being called


def copy_context(context=None) -> InferenceContext:
    """Clone a context if given, or return a fresh context."""
    if context is not None:
        return context.clone()

    return InferenceContext()


def bind_context_to_node(context: Context, node: Node) -> InferenceContext:
    """Given a context a boundnode to retrieve the correct function name or
    attribute value with from further inference.

    Do not use an existing context since the boundnode could then
    be incorrectly propagated higher up in the call stack.

    Parameters
    ----------
    context : Context
        Context to use.

    node : Node
        Node to do name lookups from.

    Returns
    -------
    ret : InferenceContext
        A new context.
    """
    context = copy_context(context)
    context.boundnode = node
    return context
