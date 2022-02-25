import sys
import os

# Once installed, k_* scripts will be avilable in the default Python path.
# During testing, we need to manually add the parent of the tests directory
# so we can find the things we're testing.
#
# In addition, we want to inject the development directory's version of
# pylib early in the path list, so we can test against that, rather than
# against any installed version.

p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if sys.path[0] != p:
    sys.path.insert(0, p)
    p2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pylib'))
    sys.path.insert(1, p2)
