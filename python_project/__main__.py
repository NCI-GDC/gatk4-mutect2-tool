#!/usr/bin/env python
"""
Python Project Template Entrypoint Script
"""

import argparse
import datetime
import logging
import sys
from typing import List, Optional

try:
    from python_project import __version__
except Exception:
    __version__ = '0.0.0'

log = logging.getLogger(__name__)


def setup_logger(args: argparse.Namespace) -> None:
    """Apply logging config from CLI args."""

    logging.basicConfig(
        level=args.log_level,
        format=args.log_format,
    )


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    # Add version args
    parser.add_argument('--version', action='version', version=__version__)

    # Add logging args
    logging_group = parser.add_argument_group("Logging")
    logging_group.add_argument(
        '--log-level',
        choices=[
            logging.INFO,
            logging.DEBUG,
            logging.CRITICAL,
            logging.WARNING,
            logging.ERROR,
        ],
        type=int,
        default=logging.INFO,
    )
    logging_group.add_argument(
        '--log-format',
        type=str,
        metavar='STR',
        default="%(asctime)s %(name)s:%(lineno)s %(levelname)s | %(message)s",
    )

    # Add additional arguments

    return parser


def process_args(argv: Optional[List] = None) -> argparse.Namespace:
    """Process args to NamedTuple."""

    parser = setup_parser()

    if argv:
        args, unknown_args = parser.parse_known_args(argv)
    else:
        args, unknown_args = parser.parse_known_args()

    if unknown_args:
        log.debug("Found unknown args: %s", unknown_args)

    return args


def run(run_args: argparse.Namespace) -> int:
    """Method for running script logic.

    Accepts:
        run_args (namespace): Collection of parsed arguments
    Returns:
        ret_code (int): Return code for sys.exit()
    """

    ret_val = 0

    start_time = datetime.datetime.now()

    log.info("Running process...")
    log.info("Version: %s", run_args.version)

    # Log runtime info
    end_time = datetime.datetime.now()
    run_time = end_time - start_time
    log.info("Run time: %d seconds", run_time.seconds)
    return ret_val


def main(argv: Optional[List[str]] = None) -> int:
    """Main Entrypoint."""
    exit_code = 0

    args = process_args(argv)

    setup_logger(args)

    log.info("Process called with %s", args)

    try:
        exit_code = run(args)
    except Exception as e:
        log.exception(e)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    """CLI Entrypoint"""

    status_code = 0
    try:
        status_code = main()
    except Exception as e:
        log.exception(e)
        sys.exit(1)
    sys.exit(status_code)


# __END__
