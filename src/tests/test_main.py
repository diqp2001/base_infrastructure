"""import unittest
import sys
import os
from main import increment  # Now use direct import

class TestMain(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(increment(4), 5)

if __name__ == '__main__':
    unittest.main()"""


import unittest
import sys
import os
def increment(x: int) -> int:
    return x + 1
# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#from src.main import increment  # Import from src.main

class TestMain(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(increment(4), 5)

if __name__ == '__main__':
    unittest.main()