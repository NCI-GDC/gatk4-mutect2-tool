#!/usr/bin/env python3

import unittest

from python_project import __main__ as MOD


class ThisTestCase(unittest.TestCase):
    def test_pass(self):
        MOD.main()


# __END__
