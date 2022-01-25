#!/usr/bin/env python3
"""
Multithreading GATK4 MuTect2
@author: Shenglai Li
"""
import argparse
import concurrent.futures
import logging
import os
import pathlib
import shlex
import subprocess
import sys
import time
from collections import namedtuple
from textwrap import dedent
from types import SimpleNamespace
from typing import Any, Callable, Generator, List, NamedTuple, Optional

from gatk4_mutect2_tool import __version__

logger = logging.getLogger(__name__)

DI = SimpleNamespace(
    subprocess=subprocess,
    futures=concurrent.futures,
)


class PopenReturn(NamedTuple):
    stderr: str
    stdout: str


CMD_STR = dedent(
    """
    {GATK_PATH}
    --java-options \"-XX:+UseSerialGC -Xmx{JAVA_HEAP}\"
    Mutect2
    --intervals {REGION}
    --arguments_file {ARGS}
    --output {OUTPUT}.{BLOCK_NUM}.vcf.gz"""
).strip()


def setup_logger() -> None:
    """
    Sets up the logger.
    """
    logger_format = "[%(levelname)s] [%(asctime)s] [%(name)s] - %(message)s"
    logger.setLevel(level=logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(logger_format, datefmt="%Y%m%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def subprocess_commands_pipe(
    cmd: str, timeout: int, di: SimpleNamespace = DI
) -> PopenReturn:
    """run pool commands"""

    output = di.subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        output_stdout, output_stderr = output.communicate(timeout=timeout)
    except Exception:
        output.kill()
        _, output_stderr = output.communicate()
        raise ValueError(output_stderr.decode())

    if output.returncode != 0:
        raise ValueError(output_stderr.decode())

    return PopenReturn(stdout=output_stdout.decode(), stderr=output_stderr.decode())


def tpe_submit_commands(
    cmds: List[Any],
    thread_count: int,
    timeout: int,
    fn: Callable = subprocess_commands_pipe,
    di: SimpleNamespace = DI,
) -> list:
    """Run commands on multiple threads.

    Stdout and stderr are logged on function success.
    Exception logged on function failure.
    Accepts:
        cmds (List[str]): List of inputs to pass to each thread.
        thread_count (int): Threads to run
        fn (Callable): Function to run using threads, must accept each element of cmds
    Returns:
        list of commands which raised exceptions
    Raises:
        None
    """
    exceptions = []
    with di.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = {executor.submit(fn, cmd, timeout): cmd for cmd in cmds}
        for future in di.futures.as_completed(futures):
            cmd = futures[future]
            try:
                result = future.result()
                logger.info(result.stdout)
                logger.info(result.stderr)
            except Exception as e:
                exceptions.append(cmd)
                logger.error(result.stdout)
                logger.error(result.stderr)
    return exceptions


def yield_bed_regions(intervals_file: str) -> Generator[str, None, None]:
    """Yield region string from BED file."""
    with open(intervals_file, "r") as fh:
        for line in fh:
            chrom, start, end, *_ = line.strip().split()
            interval = "{}:{}-{}".format(chrom, int(start) + 1, end)
            yield interval


def key_to_cmd(string: str) -> str:
    """
    translate key to cmd
    string: xx_xx_xx
    returns: --xx-xx-xx
    """
    return '--{}'.format(string.replace('_', '-'))


def process_argv(argv: Optional[List] = None) -> namedtuple:
    """
    prepare GATK4.2.4.1 Mutect2 cmd based on the python parameters.
    args: parser.parse_args()
    returns: An argument file for the gatk command
    """
    parser = setup_parser()

    if argv:
        args, unknown_args = parser.parse_known_args(argv)
    else:
        args, unknown_args = parser.parse_known_args()

    arg_file = 'argument_file'
    args_dict = vars(args)
    args_dict['extras'] = unknown_args
    exclude = [
        'output',
        'f1r2_tar_gz',
        'bam_output',
        'intervals',
        'nthreads',
        'java_heap',
        'gatk4_path',
        'extras',
    ]
    cmds = list()
    for k, v in args_dict.items():
        if k not in exclude:
            if v is not None and v is not False:
                if v is True:
                    cmds.append('{}'.format(key_to_cmd(k)))
                elif isinstance(v, str) or isinstance(v, int) or isinstance(v, float):
                    cmds.append('{} {}'.format(key_to_cmd(k), str(v)))
                elif isinstance(v, list):
                    for i in v:
                        cmds.append('{} {}'.format(key_to_cmd(k), i))
    with open(arg_file, 'w') as of:
        for arg in cmds:
            of.writelines(arg + '\n')
    args_dict['arg_file'] = os.path.abspath(arg_file)
    run_args = namedtuple('RunArgs', list(args_dict.keys()))  # type: ignore
    return run_args(**args_dict)  # type: ignore


def yield_formatted_commands(
    java_heap: int,
    gatk_path: str,
    intervals: str,
    arg_file: str,
    output_prefix: str,
    f1r2: bool,
    bamout: bool,
) -> Generator[str, None, None]:
    """Yield commands for each BED interval."""
    for i, region in enumerate(yield_bed_regions(intervals)):
        cmd = CMD_STR.format(
            GATK_PATH=gatk_path,
            JAVA_HEAP=java_heap,
            REGION=region,
            ARGS=arg_file,
            OUTPUT=output_prefix,
            BLOCK_NUM=i,
        )
        if f1r2:
            cmd += ' --f1r2-tar-gz {}.{}.tar.gz'.format(output_prefix, i)
        if bamout:
            cmd += ' --bam-output {}.{}.reassembly.bam'.format(output_prefix, i)
        yield cmd


def setup_parser() -> argparse.ArgumentParser:
    """
    Loads the parser
    """
    parser = argparse.ArgumentParser(
        prog='GATK4.2.4.1 Mutect2 multithreading wrapper.', add_help=True
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        '-I', '--input', required=True, action='append', help='BAM files.'
    )
    parser.add_argument(
        '-O',
        '--output',
        required=True,
        help='Output prefix on files to which variants should be written.',
    )
    parser.add_argument(
        '-R', '--reference', required=True, help='Reference sequence file.'
    )
    parser.add_argument(
        '--intervals',
        required=True,
        help='One or more genomic intervals over which to operate',
    )
    parser.add_argument(
        '--java_heap',
        required=True,
        help='JVM arguments to GATK. This is NOT a GATK parameter.',
    )
    parser.add_argument(
        '--nthreads',
        type=int,
        required=True,
        help='Number of threads used for this wrapper code. This is NOT a GATK parameter.',
    )
    parser.add_argument(
        '--gatk4_path',
        required=True,
        help='GATK4 executable path.',
        default='/usr/local/bin/gatk',
    )
    parser.add_argument(
        '--active-probability-threshold',
        required=False,
        help='Minimum probability for a locus to be considered active.',
    )
    parser.add_argument(
        '--adaptive-pruning-initial-error-rate',
        required=False,
        help='Initial base error rate estimate for adaptive pruning.',
    )
    parser.add_argument(
        '--af-of-alleles-not-in-resource',
        required=False,
        help='Population allele fraction assigned to alleles not found in germline resource. Please see docs/mutect/mutect2.pdf fora derivation of the.',
    )
    parser.add_argument(
        '--allow-non-unique-kmers-in-ref',
        required=False,
        help='Allow graphs that have non-unique kmers in the reference.',
        action='store_true',
    )
    parser.add_argument(
        '--assembly-region-padding',
        required=False,
        help='Number of additional bases of context to include around each assembly region.',
    )
    parser.add_argument(
        '--bam-output',
        required=False,
        help='If specified, assembled haplotypes wil be written to bam.',
        action='store_true',
    )
    parser.add_argument(
        '--bam-writer-type',
        required=False,
        help='Which haplotypes should be written to the BAM.',
    )
    parser.add_argument(
        '--base-quality-score-threshold',
        required=False,
        help='Base qualities below this threshold will be reduced to the minimum (6).',
    )
    parser.add_argument(
        '--callable-depth',
        required=False,
        help='Minimum depth to be considered callable for Mutect stats. Does not affect genotyping.',
    )
    parser.add_argument(
        '--disable-adaptive-pruning',
        required=False,
        help='Disable the adaptive algorithm for pruning paths in the graph.',
        action='store_true',
    )
    parser.add_argument(
        '--disable-bam-index-caching',
        required=False,
        help='If true, dont cache bam indexes, this will reduce memory requirements but may harm performance if many intervals are specified. Caching is automatically disabled if there are no intervals specified.',
        action='store_true',
    )
    parser.add_argument(
        '--disable-sequence-dictionary-validation',
        required=False,
        help='If specified, do not check the sequence dictionaries from our inputs for compatibility. Use at your own risk!',
        action='store_true',
    )
    parser.add_argument(
        '--disable-tool-default-annotations',
        required=False,
        help='Disable all tool default annotations.',
        action='store_true',
    )
    parser.add_argument(
        '--dont-increase-kmer-sizes-for-cycles',
        required=False,
        help='Disable iterating over kmer sizes when graph cycles are detected.',
        action='store_true',
    )
    parser.add_argument(
        '--dont-trim-active-regions',
        required=False,
        help='If specified, we will not trim down the active region from the full region (active + extension) to just the active interval for genotyping.',
        action='store_true',
    )
    parser.add_argument(
        '--dont-use-soft-clipped-bases',
        required=False,
        help='Do not analyze soft clipped bases in the reads.',
        action='store_true',
    )
    parser.add_argument(
        '--downsampling-stride',
        required=False,
        help='Downsample a pool of reads starting within a range of one or more bases.',
    )
    parser.add_argument(
        '--emit-ref-confidence',
        required=False,
        help='(BETA feature) Mode for emitting reference confidence scores.',
    )
    parser.add_argument(
        '--enable-all-annotations',
        required=False,
        help='Use all possible annotations (not for the faint of heart).',
        action='store_true',
    )
    parser.add_argument(
        '--f1r2-max-depth',
        required=False,
        help='Sites with depth higher than this value will be grouped.',
    )
    parser.add_argument(
        '--f1r2-median-mq',
        required=False,
        help='Skip sites with median mapping quality below this value.',
    )
    parser.add_argument(
        '--f1r2-min-bq',
        required=False,
        help='Exclude bases below this quality from pileup.',
    )
    parser.add_argument(
        '--f1r2-tar-gz',
        required=False,
        help='If specified, collect F1R2 counts and output files into tar.gz file.',
        action='store_true',
    )
    parser.add_argument(
        '--force-active',
        required=False,
        help='If provided, all regions will be marked as active.',
        action='store_true',
    )
    parser.add_argument(
        '--genotype-filtered-alleles',
        required=False,
        help='Whether to force genotype even filtered alleles.',
        action='store_true',
    )
    parser.add_argument(
        '--genotype-germline-sites',
        required=False,
        help='(EXPERIMENTAL) Call all apparent germline site even though they will ultimately be filtered.',
        action='store_true',
    )
    parser.add_argument(
        '--genotype-pon-sites',
        required=False,
        help='Call sites in the PoN even though they will ultimately be filtered.',
        action='store_true',
    )
    parser.add_argument(
        '--germline-resource',
        required=False,
        help='Population vcf of germline sequencing containing allele fractions.',
    )
    parser.add_argument(
        '--gvcf-lod-band',
        required=False,
        help='Exclusive upper bounds for reference confidence LOD bands (must be specified in increasing order).',
    )
    parser.add_argument(
        '--ignore-itr-artifacts',
        required=False,
        help='Turn off read transformer that clips artifacts associated with end repair insertions near inverted tandem repeats.',
        action='store_true',
    )
    parser.add_argument(
        '--initial-tumor-lod',
        required=False,
        help='Log 10 odds threshold to consider pileup active.',
    )
    parser.add_argument(
        '--interval-merging-rule',
        required=False,
        help='Interval merging rule for abutting intervals.',
    )
    parser.add_argument(
        '--kmer-size',
        required=False,
        help='Kmer size to use in the read threading assembler.',
    )
    parser.add_argument(
        '--max-assembly-region-size',
        required=False,
        help='Maximum size of an assembly region.',
    )
    parser.add_argument(
        '--max-mnp-distance',
        required=False,
        help='Two or more phased substitutions separated by this distance or less are merged into MNPs.',
    )
    parser.add_argument(
        '--max-num-haplotypes-in-population',
        required=False,
        help='Maximum number of haplotypes to consider for your population.',
    )
    parser.add_argument(
        '--max-population-af',
        required=False,
        help='Maximum population allele frequency in tumor-only mode.',
    )
    parser.add_argument(
        '--max-prob-propagation-distance',
        required=False,
        help='Upper limit on how many bases away probability mass can be moved around when calculating the boundaries between active and inactive assembly regions.',
    )
    parser.add_argument(
        '--max-reads-per-alignment-start',
        required=False,
        help='Maximum number of reads to retain per alignment start position. Reads above this threshold will be downsampled. Set to 0 to disable.',
    )
    parser.add_argument(
        '--max-suspicious-reads-per-alignment-start',
        required=False,
        help='Maximum number of suspicious reads (mediocre mapping quality or too many substitutions) allowed in a downsampling stride. Set to 0 to disable.',
    )
    parser.add_argument(
        '--max-unpruned-variants',
        required=False,
        help='Maximum number of variants in graph the adaptive pruner will allow.',
    )
    parser.add_argument(
        '--min-assembly-region-size',
        required=False,
        help='Minimum size of an assembly region.',
    )
    parser.add_argument(
        '--min-base-quality-score',
        required=False,
        help='Minimum base quality required to consider a base for calling.',
    )
    parser.add_argument(
        '--min-dangling-branch-length',
        required=False,
        help='Minimum length of a dangling branch to attempt recovery.',
    )
    parser.add_argument(
        '--min-pruning',
        required=False,
        help='Minimum support to not prune paths in the graph.',
    )
    parser.add_argument(
        '--minimum-allele-fraction',
        required=False,
        help='Lower bound of variant allele fractions to consider when calculating variant LOD.',
    )
    parser.add_argument(
        '--mitochondria-mode',
        required=False,
        help='Mitochondria mode sets emission and initial LODs to 0.',
        action='store_true',
    )
    parser.add_argument(
        '--native-pair-hmm-threads',
        required=False,
        help='How many threads should a native pairHMM implementation use.',
    )
    parser.add_argument(
        '--native-pair-hmm-use-double-precision',
        required=False,
        help='Use double precision in the native pairHmm. This is slower but matches the java implementation better.',
        action='store_true',
    )
    parser.add_argument(
        '--normal-lod',
        required=False,
        help='Log 10 odds threshold for calling normal variant non-germline.',
    )
    parser.add_argument(
        '--normal-sample',
        required=False,
        help='BAM sample name of normal(s), if any. May be URL-encoded as output by GetSampleName with -encode argument.',
    )
    parser.add_argument(
        '--num-pruning-samples',
        required=False,
        help='Number of samples that must pass the minPruning threshold.',
    )
    parser.add_argument(
        '--pair-hmm-gap-continuation-penalty',
        required=False,
        help='Flat gap continuation penalty for use in the Pair HMM.',
    )
    parser.add_argument(
        '--pair-hmm-implementation',
        required=False,
        help='The PairHMM implementation to use for genotype likelihood calculations.',
    )
    parser.add_argument(
        '--panel-of-normals',
        required=False,
        help='VCF file of sites observed in normal.',
    )
    parser.add_argument(
        '--pcr-indel-model', required=False, help='The PCR indel model to use.'
    )
    parser.add_argument(
        '--pcr-indel-qual',
        required=False,
        help='Phred-scaled PCR SNV qual for overlapping fragments.',
    )
    parser.add_argument(
        '--pcr-snv-qual',
        required=False,
        help='Phred-scaled PCR SNV qual for overlapping fragments.',
    )
    parser.add_argument(
        '--pedigree',
        required=False,
        help='Pedigree file for determining the population "founders".',
    )
    parser.add_argument(
        '--phred-scaled-global-read-mismapping-rate',
        required=False,
        help='The global assumed mismapping rate for reads.',
    )
    parser.add_argument(
        '--pruning-lod-threshold',
        required=False,
        help='Ln likelihood ratio threshold for adaptive pruning algorithm.',
    )
    parser.add_argument(
        '--recover-all-dangling-branches',
        required=False,
        help='Recover all dangling branches.',
        action='store_true',
    )
    parser.add_argument(
        '--showHidden',
        required=False,
        help='Display hidden arguments.',
        action='store_true',
    )
    parser.add_argument(
        '--sites-only-vcf-output',
        required=False,
        help='If true, dont emit genotype fields when writing vcf file output.',
        action='store_true',
    )
    parser.add_argument(
        '--smith-waterman',
        required=False,
        help='Which Smith-Waterman implementation to use, generally FASTEST_AVAILABLE is the right choice.',
    )
    parser.add_argument(
        '--tumor-lod-to-emit',
        required=False,
        help='Log 10 odds threshold to emit variant to VCF.',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        required=False,
        help="Max time for command to run, in seconds.",
    )
    return parser


def run(run_args) -> None:
    """
    Main script logic.
    Creates Mutect2 commands for each BED region and executes in multiple threads.
    """
    run_commands = list(
        yield_formatted_commands(
            run_args.java_heap,
            run_args.gatk4_path,
            run_args.intervals,
            run_args.arg_file,
            run_args.output,
            run_args.f1r2_tar_gz,
            run_args.bam_output,
        )
    )
    # Start Queue
    exceptions = tpe_submit_commands(run_commands, run_args.nthreads, run_args.timeout)
    if exceptions:
        for e in exceptions:
            logger.error(e)
        raise ValueError("Exceptions raised during processing.")

    # Check outputs
    p = pathlib.Path('.')
    outputs = list(p.glob("*.vcf.gz"))

    # Sanity check
    if len(run_commands) != len(outputs):
        logger.error("Number of output files not expected")
    return


def main(argv: list = None) -> int:
    exit_code = 0

    argv = argv or sys.argv
    args = process_argv(argv)
    setup_logger()
    start = time.time()
    import pdb

    pdb.set_trace()
    try:
        run(args)
        logger.info("Finished, took %s seconds.", round(time.time() - start, 2))
    except Exception as e:
        logger.exception(e)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    # CLI Entrypoint.
    retcode = 0

    try:
        retcode = main()
    except Exception as e:
        retcode = 1
        logger.exception(e)

    sys.exit(retcode)

# __END__
