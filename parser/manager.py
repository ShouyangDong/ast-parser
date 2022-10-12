from msilib.schema import Class
from operator import mod
from typing import ClassVar


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
        modname = None,
        fallback = False,
        source = False,
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
        if (
            modname in self.ast_cache
            and self.ast_cache[modname].file == filepath
        ):
            return self.ast_cache[modname]
        if source:
            # pylint: disable=import-outside-toplevel; circular import
            from parser.builder import Builder

            return Builder(self).file_build(filepath, modname)
        if fallback and modname:
            return self.ast_from_module_name(modname)
        raise ValueError("Unable to build an AST for {path}.", path=filepath)
