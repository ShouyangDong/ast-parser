import ast
from multiprocessing import Manager
import os
import textwrap
from typing import Union, Optional

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
