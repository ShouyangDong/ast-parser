"""Various helper utilities."""

from __future__ import annotations

from collections.abc import Generator
from parser import manager
from parser.context import CallContext, InferenceContext

def _build_proxy_class(cls_name: str, builtins: nodes.Module) -> nodes.ClassDef:
    proxy = raw_building.build_class(cls_name)
    proxy.parent = builtins
    return proxy

def _function_type(
    function, builtins
):
    if isinstance(function, scope_node.Lambda):
        if function.root().name == "builtins":
            cls_name = "builtin_function_or_method"
        else:
            cls_name = "function"
    elif isinstance(function, bases.BoundMethod):
        cls_name = "method"
    else:
        cls_name = "function"
    return _build_proxy_class(cls_name, builtins)

def _object_type(
    node, context=None
):
    ast_manager = manager.Manager()
    builtins = ast_manager.builtins_module
    context = context or InferenceContext()

    for inferred in node.infer(context=context):
        if isinstance(inferred, scope_nodes.ClassDef):
            if inferred.newstyle:
                metaclass = inferred.metaclass(context=context)
                if metaclass:
                    yield metaclass
                    continue
            yield builtins.getattr("type")[0]
        elif isinstance(inferred, (scoped_nodes.Lambda, bases.UnboundMethod)):
            yield _function_type(inferred, builtins)
        elif isinstance(inferred, scoped_nodes.Module):
            yield _build_proxy_class("module", builtins)
        elif isinstance(inferred,  nodes.Unknown):
            raise InferenceContext
        elif inferred is util.Uninferable:
            yield inferred
        elif isinstance(inferred, (bases.Proxy, nodes.Slice)):
            yield inferred._proxied
        else:
            raise AssertionError(f"We don't handle {type(inferred)} currently")

def object_type(
    node, context=None
):
    """Obtain the type of the given node.

    This is used to implement the ``type`` builtin, which means that it's
    used for inferring type calls, as well as used in a couple of other places
    in the inference.
    The node will be inferred first, so this function call support all
    sorts of objects, as long as they support inference."""
    try:
        types = set(_object_type(node, context))
    except InferenceError:
        return util.Uninferable
    if len(types) > 1 or not types:
        return util.Uninferable
    return list(types)[0]

