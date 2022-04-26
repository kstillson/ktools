'''
During testing, we need to manually add the parent of the tests directory
so we can find the things we're testing.

Note: each context file needs to be named differently, or it will interfere
with loading other context scripts if tests are run in the same session.

'''

import sys
import os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if sys.path[0] != p: sys.path.insert(0, p)
