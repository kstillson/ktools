
import sys
import os
p0 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../home_control'))
p1 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))  # for kcore
if sys.path[0] != p0:
    sys.path.insert(0, p0)
    sys.path.insert(1, p1)

