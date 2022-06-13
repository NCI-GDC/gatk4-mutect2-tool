#!/usr/bin/env python3
"""
Modify GATK4.1.2 Mutect2 VCF sample header to "TUMOR", "NORMAL"

@author: Shenglai Li
"""
import logging
from typing import Optional

import click
import pysam

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

tumor_bamT = str
normal_bamT = Optional[str]
vcfT = str
outputT = str


def get_sample_name(bam: str) -> str:
    '''
    Get sample name from BAM file
    '''
    sample: str
    b = pysam.AlignmentFile(bam, 'rb')
    sample = b.header['RG'][0]['SM']  # type: ignore
    return sample


def modify_vcf_sample(
    tumor_bam: tumor_bamT, normal_bam: normal_bamT, vcf: vcfT, output: outputT
) -> None:
    '''
    Modify VCF sample in the header
    '''
    out_vcf = output
    reader = pysam.BGZFile(vcf, mode='rb')  # type: ignore
    writer = pysam.BGZFile(out_vcf, mode='wb')  # type: ignore
    try:
        for line in reader:
            new_line: str
            new_line = line.decode('utf-8')
            if new_line.startswith('#CHROM'):
                if normal_bam:
                    assert (
                        normal_bam in new_line
                    ), f'Unable to find normal sample tag in the vcf file. {normal_bam}'
                    new_line = new_line.replace(f'{normal_bam}', 'NORMAL')
                assert (
                    tumor_bam in new_line
                ), f'Unable to find tumor sample tag in the vcf file. {tumor_bam}'
                new_line = new_line.replace(f'{tumor_bam}', 'TUMOR')
                writer.write(str.encode(f"{new_line}\n", encoding='utf-8'))
            else:
                new_line = new_line + '\n'
                writer.write(new_line.encode('utf-8'))
    except AssertionError as e:
        logger.exception(e)
    finally:
        writer.close()
        reader.close()
    pysam.tabix_index(out_vcf, preset='vcf', force=True)


@click.command()
@click.option('--tumor_bam', required=True, type=tumor_bamT)
@click.option('--vcf', required=True, type=vcfT)
@click.option('--output', required=True, type=outputT)
@click.option('--normal_bam', required=False, type=normal_bamT)
def main(
    tumor_bam: tumor_bamT,
    vcf: vcfT,
    output: outputT,
    normal_bam: normal_bamT = None,
) -> None:
    '''
    main
    '''
    tumor_sample = get_sample_name(tumor_bam)
    logger.info(f'{tumor_sample=}')
    normal_sample = None
    if normal_bam:
        normal_sample = get_sample_name(normal_bam)
    logger.info(f'{normal_sample=}')
    modify_vcf_sample(tumor_sample, normal_sample, vcf, output)


if __name__ == "__main__":
    main()

# __END__
