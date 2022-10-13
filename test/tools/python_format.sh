# black format
black  parser/
black  test/
pyupgrade --py38-plus parser/*.py
pyupgrade --py38-plus test/python/*.py
pydocstringformatter --style=pep257 --write --no-split-summary-body --capitalize-first-letter parser/*.py
pydocstringformatter --style=pep257 --write --no-split-summary-body --capitalize-first-letter test/python/*.py
