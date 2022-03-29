
# Once installed, scripts will be avilable in the default Python path.
# During testing, we need to manually add the parent of the tests directory
# so we can find the things we're testing.

# Note: each context file needs to be named differently, or it will interfere
# with loading other context scripts if tests are run in the same session.

import sys
import os
p1 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tools'))
p2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if sys.path[0] != p1:
    sys.path.insert(0, p2)
    sys.path.insert(0, p1)
    print('new path: %s' % sys.path)

