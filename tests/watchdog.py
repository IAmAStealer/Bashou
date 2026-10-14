"""Runs the tests like `python3 -m unittest -v`, but a test stuck for 3 minutes prints where it waits and
stops the run (CI on macOS hung for 6 hours with no clue, 2026-10-14).

    python3 -m tests.watchdog [module ...]
"""

import faulthandler
import sys
import unittest

LIMIT = 180


class Result(unittest.TextTestResult):
    def startTest(self, test):
        faulthandler.dump_traceback_later(LIMIT, exit=True)
        super().startTest(test)

    def stopTest(self, test):
        faulthandler.cancel_dump_traceback_later()
        super().stopTest(test)


if __name__ == "__main__":
    unittest.main(module=None, argv=[sys.argv[0]] + (["-v"] + sys.argv[1:] if sys.argv[1:] else ["discover", "-v"]),
                  testRunner=unittest.TextTestRunner(resultclass=Result, verbosity=2))
