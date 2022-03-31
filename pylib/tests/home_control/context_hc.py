
import sys
import os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../home_control'))
if sys.path[0] != p: sys.path.insert(0, p)
