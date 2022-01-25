#!/usr/bin/env python3
import sys

from gatk4_mutect2_tool import multi_gatk4_mutect2

if __name__ == "__main__":
    # CLI Entrypoint.
    retcode = 0

    try:
        retcode = multi_gatk4_mutect2.main()

    except Exception as e:
        retcode = 1

    sys.exit(retcode)

# __END__
