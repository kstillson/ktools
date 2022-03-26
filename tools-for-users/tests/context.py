
# Once installed, k_* scripts will be avilable in the default Python path.
# During testing, we need to manually add the parent of the tests directory
# so we can find the things we're testing.

import sys
import os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if sys.path[0] != p: sys.path.insert(0, p)
