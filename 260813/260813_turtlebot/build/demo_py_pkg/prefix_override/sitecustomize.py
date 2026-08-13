import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/pa4/turtlebot3_ws/src/260813/install/demo_py_pkg'
