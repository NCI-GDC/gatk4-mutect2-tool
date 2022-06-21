#!/usr/bin/env python3

import unittest

from click.testing import CliRunner

from gatk4_mutect2_tool import modify_vcf_sample as MOD


class ThisTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.cli_args_dict = {
            "--normal_bam": "normal.bam",
            "--tumor_bam": "tumor.bam",
            "--vcf": "test.vcf",
            "--output": "output.vcf",
        }
        self.cli_args_list = []
        for k, v in self.cli_args_dict.items():
            self.cli_args_list.extend([k, v])

    def cli_args(self):
        runner = CliRunner()
        result = runner.invoke(MOD.main, self.cli_args_list)
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()

# __END__
