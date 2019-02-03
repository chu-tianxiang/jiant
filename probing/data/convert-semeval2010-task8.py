#!/usr/bin/env python

# Script to convert SemEval 2010 Task 8 data into edge probing format.
#
# Download the data from
# https://docs.google.com/document/d/1QO_CnmvNRnYwNWu1-QCAeR5ToQYkXUqFeAJbdEhsq7w/preview
# (yes, that's actually the website) and unzip SemEval2010_task8_all_data.zip
#
# Usage:
#   ./convert-semeval2010-task8.py \
#       -i <semeval_dir>/SemEval2010_task8_<split>/<filename>.txt \
#       -o /path/to/probing/data/semeval-2010-task8
#

import sys
import os
import json
import re
import collections
import argparse

import logging as log
log.basicConfig(format='%(asctime)s: %(message)s',
                datefmt='%m/%d %I:%M:%S %p', level=log.INFO)

import utils
import numpy as np
import pandas as pd
from tqdm import tqdm

from typing import Dict, Tuple, Iterable

def parse_lines(lines: Iterable[str]) -> Iterable[Tuple[str, str, str]]:
    """Parse the SemEval 2010 data format.

    See SemEval2018_task8_all_data/SemEval2010_task8_training/README.txt
    Format is:

    12 "Text of the sentence with <e1>entity</e1> tags"
    Label(e1, e2)
    Comment: text from the annotator explaining the label
    """
    current = []
    for line in lines:
        if not line.strip():
            if current:
                assert len(current) == 3
                yield tuple(current)
            current = []
            continue
        current.append(line)
    if current:
        assert len(current) == 3
        yield tuple(current)

TAG_MATCHER = r"</?e(\d+)>"
TAG_MATCHER_START = r".*<e(\d+)>.*"
TAG_MATCHER_END = r".*</e(\d+)>.*"

def get_entity_spans(tagged_tokens):
    spans = collections.defaultdict(lambda: [None, None])
    for i, token in enumerate(tagged_tokens):
        m = re.match(TAG_MATCHER_START, token)
        if m:
            spans[int(m.group(1))][0] = i      # inclusive
        m = re.match(TAG_MATCHER_END, token)
        if m:
            spans[int(m.group(1))][1] = i + 1  # exclusive
    spans.default_factory = None
    # Validate spans to make sure both are complete.
    assert set(spans.keys()) == {1,2}
    for span in spans.values():
        assert len(span) == 2
        assert span[0] is not None
        assert span[1] is not None
    return spans

def record_from_triple(sentence_line, label, comment_line):
    record = {}
    m = re.match(r'^(\d+)\s+"(.*)"\s*$', sentence_line)
    assert m is not None
    id, tagged_sentence = m.groups()
    tagged_tokens = tagged_sentence.split()
    clean_tokens = [re.sub(TAG_MATCHER, "", t) for t in tagged_tokens]
    record['text'] = " ".join(clean_tokens)
    record['info'] = {'id': int(id)}

    spans = get_entity_spans(tagged_tokens)
    target = {}
    target['label'] = label
    target['span1'] = spans[1]
    target['span2'] = spans[2]
    target['info'] = {'comment': re.sub(r"Comment:\s*", "", comment_line)}
    record['targets'] = [target]
    return record

def write_file_and_print_stats(records, target_fname):
    stats = utils.EdgeProbingDatasetStats()
    records = stats.passthrough(records)
    utils.write_json_data(target_fname, records)
    log.info("Wrote examples to %s", target_fname)
    log.info(stats.format())

def convert_file(fname: str, target_fname: str):
    triples = parse_lines(utils.load_lines(fname))
    records = (record_from_triple(*t) for t in triples)
    write_file_and_print_stats(records, target_fname)

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', dest='inputs', type=str, nargs="+",
                        help="Input files (JSON) for TACRED splits.")
    parser.add_argument('-o', dest='output_dir', type=str, required=True,
                        help="Output directory.")
    args = parser.parse_args(args)

    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    pd.options.display.float_format = '{:.2f}'.format
    for fname in args.inputs:
        log.info("Converting %s", fname)
        fname_base = os.path.basename(fname).lower()
        target_fname = os.path.join(args.output_dir,
                                    os.path.splitext(fname_base)[0] + ".json")
        convert_file(fname, target_fname)


if __name__ == '__main__':
    main(sys.argv[1:])
    sys.exit(0)


