
# Note: this has to have a different name from the one in circuitpy_lib,
# otherwise when we run the tests here that are symlinked to
# circuitpy_lib/tests, they'll run that context file, which puts its
# directory at the head of pythonpath.  Then when the next test runs
# "import context", it imports the context from circuitpy_lib/tests,
# and we end up importing the wrong stuff.  ick.

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
