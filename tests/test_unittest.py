"""import src.main as main    # The code to test

def test_increment():
    assert main.increment(4) == 4"""

import unittest
import src.main as main  # Adjust if your path differs

class TestMain(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(main.increment(4), 5)

if __name__ == '__main__':
    unittest.main()