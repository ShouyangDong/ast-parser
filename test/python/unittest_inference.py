import unittest
import pytest

from parser.builder import parse


def test_simple_tuple() -> None:
    module = parse(
        """
        a = (1, )
        b = (22, )
        some = a + b
        """
    )

    print("[INFO]**************module", module)


if __name__ == "__main__":
    test_simple_tuple()
