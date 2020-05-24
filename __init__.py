import os
from . import _utils

cmdSupport =  _utils.cmdSupport
hint =  _utils.hint

for module in os.listdir(os.path.dirname(__file__)):
    if module in ['__init__.py', '_utils.py'] or module[-3:] != '.py':
        continue
    __import__(module[:-3], globals(), locals(), level=1)

del module
