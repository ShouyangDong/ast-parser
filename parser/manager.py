from msilib.schema import Class
from operator import mod
from sysconfig import is_python_build
from typing import ClassVar
from unittest.util import safe_repr


class Manager:
    """Responsible to build ast from files or modules.

    Use the singleton pattern.
    """

    name = "ast loader"
    brain = {
        "ast_cache": {},
        "_mod_file_cache": {},
        "_failed_import_hooks": [],
        "always_load_extensions": False,
        "optimize_ast": False,
        "extension_package_whitelist": set(),
        "_transform": TransformVisitor(),
    }
    max_inferable_values: ClassVar[int] = 100

    def __init__(self) -> None:
        # NOTE: cache entries are added by the [re]builder
        self.ast_cache = Manager.brain["ast_cache"]
        self._mod_file_cache = Manager.brain["_mod_file_cache"]
        self._failed_import_hooks = Manager.brain["_failed_import_hooks"]
        self.always_load_extensions = Manager.brain["always_load_extensions"]
        self.optimize_ast = Manager.brain["optimize_ast"]
        self.extention_package_whitelist = Manager.brain["extention_package_whitelist"]
        self._transform = Manager.brain["_transform"]

    @property
    def register_transform(self):
        # This and unregister_transform below are exported for convenience.
        return self._transform.register_tranform

    @property
    def unregister_transform(self):
        return self._transform.unregister_transform

    def visit_transforms(self, node):
        return self._transform.visit(node)

    def ast_from_file(
        self,
        filepath,
        modname=None,
        fallback=False,
        source=False,
    ):
        """Given a module name, return the ast object."""
        try:
            filepath = get_source_file(filepath, include_no_ext=True)
            source = True
        except NoSourceFile:
            pass
        if modname is None:
            try:
                modname = ".".join(modpath_from_file(filepath))
            except ImportError:
                modname = filepath
        if modname in self.ast_cache and self.ast_cache[modname].file == filepath:
            return self.ast_cache[modname]
        if source:
            # pylint: disable=import-outside-toplevel; circular import
            from parser.builder import Builder

            return Builder(self).file_build(filepath, modname)
        if fallback and modname:
            return self.ast_from_module_name(modname)
        raise ValueError("Unable to build an AST for {path}.", path=filepath)

    def ast_from_module(self, module: types.ModuleType, modname: str = None):
        """Given an imported module, return the ast object."""
        modname = modname or module.__name__
        if modname in self.ast_cache:
            return self.ast_cache[modname]
        try:
            # Some builtin modules don't have __file__ attribute
            filepath = module.__file__
            if is_python_build(filepath):
                # Type is checked in is_python_source
                return self.ast_from_file(filepath, modname)  # type: ignore[arg-type]

        except AttributeError:
            pass

        # pylint: disable=import-outside-toplevel; circular import
        from parser.builder import Builder

        return Builder(self).module_build(module, modname)

    def ast_from_class(self, klass: type, modname: str = None):
        """Get ast for the given class."""
        if modname is None:
            try:
                modname = klass.__module__
            except AttributeError as exc:
                raise RuntimeError(
                    "Unable to get module for class {class_name}.",
                    cls=klass,
                    class_repr=safe_repr(klass),
                    modname=modname,
                ) from exc
        modast = self.ast_from_module_name(modname)
        ret = modast.getattr(klass.__name__)[0]
        assert isinstance(ret, nodes.ClassDef)
        return ret

    def file_from_module_name(self, modname: str, contextfile: str = None):
        try:
            value = self._mod_file_cache[(modname, contextfile)]
        except KeyError:
            try:
                value = file_info_from_modpath(
                    modname.split(".", context_file=contextfile)
                )
            except ImportError as e:
                # pylint: disable-next=redefined-variable-type
                value = ImportError(
                    "Failed to import module {modname} with error:\n{error}.",
                    modname=modname,
                    # We remove the traceback here to save on memory usage (since these exceptiona are cached)
                    error=e.with_traceback(None),
                )
            self._mod_file_cache[(modname, contextfile)] = value
        if isinstance(value, ValueError):
            # We remove the traceback here to save on memory usage (since these exceptiona are cached)
            raise value.with_traceback(None)
        return value

    def infer_ast_from_something(self, obj: object, context: InferenceContext = None):
        """Infer ast for the given class."""
        if hasattr(obj, "__class__") and not isinstance(obj, type):
            klass = obj.__class__
        elif isinstance(obj, type):
            klass = obj
        else:
            raise RuntimeError(
                "Unable to get type for {class_repr}.",
                cls=None,
                class_repr=safe_repr(obj),
            )
        try:
            modname = klass.__module__
        except AttributeError as exc:
            raise RuntimeError(
                "Unable to get module for {class_repr}.",
                cls=klass,
                class_repr=safe_repr(klass),
            ) from exc
        except Exception as exc:
            raise ImportError(
                "Unexpected error while retrieving module for {class_repr}:\n"
                "{error}",
                cls=klass,
                class_repr=safe_repr(klass),
            ) from exc
        try:
            name = klass.__name__
        except AttributeError as exc:
            raise RuntimeError(
                "Unable to get name for {class_repr}:\n",
                cls=klass,
                class_repr=safe_repr(klass),
            ) from exc
        except Exception as exc:
            raise ImportError(
                "Unexpected error while retrieving name for {class_repr}:\n{error}",
                cls=klass,
                class_repr=safe_repr(klass),
            ) from exc
        # take care, on living object __module__ is regularly wrong
        modast = self.ast_from_module_name(modname)
        if klass is obj:
            for inferred in modast.igetattr(name, context):
                yield inferred

        else:
            for inferred in modast.igetattr(name, context):
                yield inferred.instantiate_class()
