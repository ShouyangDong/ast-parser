import ast
import os
import textwrap
from Typing import Union, Optional

def parse(
    code: str,
    module_name: str = "",
    path: Optional[str] = None,
    apply_transforms: Optional[bool] = True,
):
    """Parses a source string in order to obtain an astroid AST from it."""
    code = textwrap.dedent(code)
    return code
