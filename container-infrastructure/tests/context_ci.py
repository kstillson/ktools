'''
Once installed, scripts will be avilable in the default Python path.
During testing, we need to manually add the parent of the tests directory
so we can find the things we're testing.

Note: each context file needs to be named differently, or it will interfere
with loading other context scripts if tests are run in the same session.
'''

import sys
import os

# allow import of files under test to resolve in-tree
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if sys.path[0] != p: sys.path.insert(0, p)

# allow imports like "kcore.common" and "ktools.ktools_settings" to resolve in-tree
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pylib'))
if sys.path[0] != p: sys.path.insert(0, p)

# Note: for the above to actually work for ktools.ktools_settings, one needs a symlink
# in "pylib" pointing from "ktools" -> "tools".  <sigh>
