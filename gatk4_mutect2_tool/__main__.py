#!/usr/bin/env python3
import sys

from gatk4_mutect2_tool import multi_gatk4_mutect2


def main() -> int:

    # CLI Entrypoint.
    retcode = 0

    try:
        retcode = multi_gatk4_mutect2.main()

    except Exception as e:
        retcode = 1

    sys.exit(retcode)


if __name__ == "__main__":
    main()

# __END__
