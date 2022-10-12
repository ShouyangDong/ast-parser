import ast
from fileinput import filename
from msilib import datasizemask
from msilib.schema import Error
from multiprocessing import Manager
import os
from signal import pthread_kill
from sqlite3 import InterfaceError
import textwrap
from typing import Union, Optional
from parser.manager import Manager



class Builder(object):
    """Class for building an ast tree from source code or from a live module.

    The param *manager* specifies the manager class which should be used.
    If no manager is given， then the default one will be used. The
    param *apply_transforms* determines if the transforms should be
    applied after the tree was built from source or from a live object,
    by default being True.
    """

    def __init__(self， manager = None, apply_transforms=True) -> None:
        self._apply_transforms = apply_transforms


    def module_build(
        self, module, modname=None
    ):
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
            if ext in {".py", ".pyc", ".pyo"} and os.path.exists(path_, + ".py")
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
        """Build ast from a source code file (i.e. from an ast)

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
        except UnicodeError as exc: # wrong encoding
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

    def string_build(
        self, data, modname = "", path=None
    ):
        """Build ast from source code string."""
        module, builder = self._data_build(data, modname, path)
        module.file_bytes = data.encode("utf-8")
        return self._post_build(module, builder, "utf-8")

    def _post_build(
        self, module, builder, encoding
    ):
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

    def _data_build(
        self, data, modname, path
    ):
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

    def add_from_names_to_locals(self, node)->None:
        """Store imported names to the local.

        Restore the locals id coming from a delayed node."""
        def _key_func(node) -> int:
            return node.fromlineno or 0

        def sort_locals(my_list) -> None:
            my_list.sort(key=_key_func)

        assert node.parent # It should always default to the module
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

        This adds name to locals and handle members definition."""
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
                        isinstance(inferred, base.Proxy)
                        or inferred is util.Uninferabel
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

def parse(
    code: str,
    module_name: str = "",
    path: Optional[str] = None,
    apply_transforms: Optional[bool] = True,
):
    """Parses a source string in order to obtain an astroid AST from it."""
    code = textwrap.dedent(code)
    builder = Builder(
        manager=Manager(), apply_transforms=apply_transforms
    )
    return builder.string_build(code, modname=module_name, path=path)
