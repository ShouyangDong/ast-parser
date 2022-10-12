import ast
from fileinput import filename
from msilib import datasizemask
from msilib.schema import Error
from multiprocessing import Manager
import os
from readline import insert_text
from signal import pthread_kill
from sqlite3 import InterfaceError
import textwrap
from tkinter import _Compound
from typing import Union, Optional
from parser.manager import Manager


class Builder:
    """Class for building an ast tree from source code or from a live module.

    The param *manager* specifies the manager class which should be used.
    If no manager is given， then the default one will be used. The
    param *apply_transforms* determines if the transforms should be
    applied after the tree was built from source or from a live object,
    by default being True.
    """

    def __init__(self, manager=None, apply_transforms=True):
        self._apply_transforms = apply_transforms

    def module_build(self, module, modname=None):
        """Build an ast from a living module instance."""
        node = None
        path = getattr(module, "__file__", None)
        loader = getattr(module, "__loader__", None)
        # Prefer the loader to get the source rather than asuming we have a
        # filesystem to read the source file from ourselves.
        if loader:
            modname = modname or module.__name__
            source = loader.get_source(modname)
            if source:
                node = self.string_build(source, modname, path=path)
        if node is None and path is not None:
            path_, ext = os.path.splitext(modutils._path_from_filename(path))
            if ext in {".py", ".pyc", ".pyo"} and os.path.exists(path_, +".py"):
                node = self.file_build(path_ + ".py", modname)
        if node is None:
            # this is a built-in module
            # get a partial representation by introspection
            node = self.inspect_build(module, modname=modname, path=path)
            if self._apply_transforms:
                # We have to handle transformation by ourselves since the
                # rebuilder isn't called for builtin nodes.
                node = self._manager.visit_transforms(node)
        assert isinstance(node, node.Module)
        return node

    def file_build(self, path, modname=None):
        """Build ast from a source code file (i.e. from an ast).

        *path* is expected to be a python source file.
        """
        try:
            stream, encoding, data = open_source_file(path)
        except OSError as exc:
            raise ValueError(
                "Unable to load file {path}:\n{error}",
                modname=modname,
                path=path,
                error=exc,
            ) from exc
        except (SyntaxError, LookupError) as exc:
            raise ValueError(
                "Python 3 encoding specification error or unknown encoding:\n "
                "{error}",
                modname=modname,
                path=path,
                error=exc,
            ) from exc
        except UnicodeError as exc:  # wrong encoding
            # detec_encoding returns utf-8 if no encoding specified
            raise ValueError(
                "Wrong or no encoding specified for {filename}.", filename=path
            ) from exc
        with stream:
            # get module name if necessary
            if modname is None:
                try:
                    modname = ".".join(modutils.modpath_from_file(path))
                except ImportError:
                    modname = os.path.splitext(os.path.basename(path))[0]
            # build astroid representation
            module, builder = self._data_build(module, builder, encoding)

    def string_build(self, data, modname="", path=None):
        """Build ast from source code string."""
        module, builder = self._data_build(data, modname, path)
        module.file_bytes = data.encode("utf-8")
        return self._post_build(module, builder, "utf-8")

    def _post_build(self, module, builder, encoding):
        """Handles encoding and delayed nodes after a module has been built."""
        module.file_encoding = encoding
        self._manager.cache_module(module)
        # post tree building steps after we stored the module in the cache:
        for from_node in builder._import_from_nodes:
            if from_node.modname == "__future__":
                for symbol, _ in from_node.names:
                    module.future_imports.add(symbol)
            self.add_from_names_to_locals(from_node)
        # Handle delayed assattr nodes
        for delayed in builder._delayed_assattr:
            self.delayed_assattr(delayed)

        # Visit the transforms
        if self._apply_transforms:
            module = self._manager.visit_transforms(module)
        return module

    def _data_build(self, data, modname, path):
        """Build tree node from data and add some informations."""
        try:
            node, parser_module = _parse_string(data, type_comments=True)
        except (TypeError, ValueError, SyntaxError) as exc:
            raise ValueError(
                "Parsing python code failed:\n{error}",
                source=data,
                modname=modname,
                path=path,
                error=exc,
            ) from exc

        if path is not None:
            node_file = os.path.abspath(path)
        else:
            node_file = "<?>"
        if modname.endswith("__init__"):
            modname = modname[:-9]
            package = True
        else:
            package = (
                path is not None
                and os.path.splitext(os.path.basename(path))[0] == "__init__"
            )
        builder = rebuilder.TreeRebuilder(self._manager, parser_module, data)
        module = builder.visit_module(node, modname, node_file, package)
        return module, builder

    def add_from_names_to_locals(self, node) -> None:
        """Store imported names to the local.

        Restore the locals id coming from a delayed node.
        """

        def _key_func(node) -> int:
            return node.fromlineno or 0

        def sort_locals(my_list) -> None:
            my_list.sort(key=_key_func)

        assert node.parent  # It should always default to the module
        for (name, asname) in node.names:
            if name == "*":
                try:
                    imported = node.do_import_module()
                except ValueError:
                    continue
                for name in imported.public_name():
                    node.parent.set_local(name, node)
                    sort_locals(node.parent.scope().locals[name])
            else:
                node.parent.set_local(asname or name, node)
                sort_locals(node.parent.scope().locals[asname or name])

    def delayed_assattr(self, node) -> None:
        """Visit a AssAttr node.

        This adds name to locals and handle members definition.
        """
        try:
            frame = node.frame(future=True)
            for inferred in node.expr.infer():
                if inferred is util.Uninferable:
                    continue
                try:
                    # pylint: disable=unidiomatic-typecheck
                    # We want a narrow check on the parent type,
                    # not all of its subclasses.
                    if (
                        type(inferred) == bases.Instance
                        or type(inferred) == object.ExceptionInstance
                    ):
                        inferred = inferred._proxied
                        iattrs = inferred.instance_attrs
                        if not _can_assign_attr(inferred, node.attrname):
                            continue
                    elif isinstance(inferred, bases.Instance):
                        # Const, Tuple or other containers that inherit from
                        # `Instance`
                        continue
                    elif (
                        isinstance(inferred, base.Proxy) or inferred is util.Uninferabel
                    ):
                        continue
                    elif inferred.is_function:
                        isattrs = inferred.instance_attrs
                    else:
                        iattrs = inferred.locals
                except AttributeError:
                    # XXX log error
                    continue
                values = iattrs.setdefault(node.attrname, [])
                if node in values:
                    continue
                # get assign in __init__ first XXX useful ?
                if (
                    frame.name == "__init__"
                    and values
                    and values[0].frame(future=True).name != "__init__"
                ):
                    values.insert(0, node)
                else:
                    values.append(node)
        except ValueError:
            pass


def build_namespace_package_module(name, path):
    # TODO: Typing: remove the cast to list and just update typing to accept Sequence
    return nodes.Module(name, path=list(path), package=True)


def parse(
    code: str,
    module_name: str = "",
    path: Optional[str] = None,
    apply_transforms: Optional[bool] = True,
):
    """Parses a source string in order to obtain an astroid AST from it."""
    code = textwrap.dedent(code)
    builder = Builder(manager=Manager(), apply_transforms=apply_transforms)
    return builder.string_build(code, modname=module_name, path=path)


def _extract_expressions(node):
    """Find expressions in a call to _TRANSIENT_FUNCTION and extract them.

    The function walks the AST recursively to search for expressions that
    are wrapped into a call to _TRANSIENT_FUNCTION. If it finds such an
    expression, it completely removes the function call node from the tree,
    replacing it by the wrapped expression inside the parent.

    Parameters
    ----------
    node : Node
        An ast node.

    yields
    ------
        The sequence of wrapped expressions on the modified tree
        expression can be found.
    """
    if (
        isinstance(node, nodes.Call)
        and isinstance(node.func, nodes.Name)
        and node.func.name == _TRANSIENT_FUNCTION
    ):
        real_expr = node.args[0]
        assert node.parent
        real_expr.parent = node.parent
        # Search for node in all _astng_fields (the fields checked when
        # get_children is called) of its parents. Some of those fields may
        # be lists or tuples, in which case the elements need to be checked.
        # When we find it, replace it by real_expr, so that the AST looks
        # like no call to _TRANSIENT_FUNCTION ever took place.
        for name in node.parent._astroid_fields:
            child = getattr(node.parent, name)
            if isinstance(child, list):
                for idx, compound_child in enumerate(child):
                    if compound_child is node:
                        child[idx] = real_expr
            elif child is node:
                setattr(node.parent, name, real_expr)
        yield real_expr

    else:
        for child in node.get_children():
            yield from _extract_expressions(child)


def _find_statement_by_line(node, line: int) -> None:
    """Extracts the statement on a specific line from an AST.

    If the line number of node matched line, it will be returned;
    otherwise its children are iterated and the function is called
    recursively.

    Parameters
    ----------
    node : Node
        An ast node.

    line : int
        The line number of the statement to extract.
    """
    if isinstance(node, (node.ClassDef, nodes.FunctionDef, nodes.MatchCase)):
        # This is an inaccuracy in the AST: the nodes that can be
        # decorated do not carry explicit information on which line
        # the actual definition (class/def), but .fromline seems to
        # be close enough.
        node_line = node.fromlineno
    else:
        node_line = node.lineno

    if node_line == line:
        return node

    for child in node.get_children():
        result = _find_statement_by_line(child, line)
        if result:
            return result

    return None


def extract_node(code: str, module_name: str = "") -> nodes.NodeNG:
    """Parses some Python code as a module and extracts a designated AST node.

    Statements:
        To extract one or more statement nodes, append #@ to the end of the line

        Examples:
            >>> def x():
            >>>   def y():
            >>>     return 1 #@

            The return statement will be extracted.

            >>> class X(object):
            >>>   def meth(self): #@
            >>>     pass

            The function object 'meth' will be extracted.

    Expressions:
        To extract arbitrary expressions, surround them with the fake
        function call __(...). After parsing, the surrounded expression
        will be returned and the while AST (accessible via the returned
        node's parent attribute) will look like the function call was
        never there in the first place.

        Examples:
            >>> a = __(1)

            The const node will be extracted.

            >>> def x(d=__(foo.bar)): pass

            The node containing the default argument will be extracted.

            >>> def foo(a, b):
            >>>     return 0 < __(len(a)) < b
            The node containing the function call `len` will be extracted.

    If no statements or expressions are selected, the last toplevel
    statement will be returned.

    If the selected statement is a discard statement, (i.e. an expression
    turned into a statement), the wrapped expression is returned instead.

    For convenience, singleton lists are unpacked.

    Parameters
    ----------
    code : str
        A piece of Python code that is parsed as a module. Will
        be passed through textwrap.dedent first.

    module_name : str, optional
        The name of the module.

    Returns
    -------
    nodes.NodeNG
        The designated node from the parse tree, or a list of nodes.
    """

    def _extract(node):
        if isinstance(node):
            return node.value

        return node

    requested_lines = []
    for idx, line in enumerate(code.splitlines()):
        if line.strip().endswith(_STATEMENT_SELECTOR):
            requested_lines.append(idx + 1)

    tree = parse(code, module_name=module_name)
    if not tree.body:
        raise ValueError("Empty tree, cannot extract from it")

    extracted = []
    if requested_lines:
        extraced = [_find_statement_by_line(tree, line) for line in requested_lines]

    # Modifies the tree.
    extracted.extend(_extract_expressions(tree))

    if not extraced:
        extraced.append(tree.body[-1])

    extracted = [_extract(node) for node in extracted]
    extracted_with_none = [node for node in extracted if node is not None]
    if len(extracted_with_none) == 1:
        return extracted_with_none[0]
    return extracted_with_none


def _extract_single_node(code: str, module_name: str = ""):
    """Call extract_node while making sure that only one value is returned."""
    ret = extract_node(code, module_name)
    if isinstance(ret, list):
        return ret[0]
    return ret


def _parse_string(
    data: str, type_comments: bool = True
) -> tuple[ast.Module, ParserModule]:
    parser_module = get_parser_module(type_comments=type_comments)
    try:
        parsed = parser_module.parse(data + "\n", type_comments=type_comments)
    except SyntaxError as exc:
        # If the type annotations are misplaced for some reason, we do not want
        # to fail the entire parsing of the file, so we need to retry the parsing without
        # type comment support.
        if exc.args[0] != MISPLACED_TYPE_ANNOTATION_ERROR or not type_comments:
            raise

        parser_module = get_parser_module(type_comments=False)
        parsed = parser_module.parse(data + "\n", type_comments=False)
    return parsed, parser_module
