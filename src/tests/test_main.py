import unittest
import sys
import os
from main import increment  # Now use direct import

class TestMain(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(increment(4), 5)

if __name__ == '__main__':
    unittest.main()