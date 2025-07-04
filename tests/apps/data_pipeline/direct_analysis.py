#!/usr/bin/env python3
import os
import sys

# Change to the correct directory
os.chdir('/home/graham/workspace/experiments/cc_executor/tests/apps/data_pipeline')

# Now execute the analyze_sales.py script content
exec(open('analyze_sales.py').read())