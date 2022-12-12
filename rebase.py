#!/usr/bin/python

import gc
import os
import re
import signal
import struct
import sys
from operator import itemgetter

import numpy as np
from numpy import sort

chars = r"A-Za-z0-9/\-:.,_$%'\"()[\]<> "
min_length = 10
table_base = {}
table_thumb_base = {}
top_score = 0
top_score_thumb = 0

regexp = "[%s]{%d,}" % (chars, min_length)
pattern = re.compile(regexp)
regexpc = "[%s]{1,}" % chars
patternc = re.compile(regexpc)


def high_scores(signal, frame):
    print "\nTop 20 base address candidates from ARM:"
    for score in sorted(table_base.items(), key=lambda d: d[1], reverse=True)[:20]:
        print "0x%x\t%d" % score
    print "\nTop 20 base address candidates from THUMB:"
    for score in sorted(table_thumb_base.items(), key=lambda d: d[1], reverse=True)[:20]:
        print "0x%x\t%d" % score

    merge_table = table_base.update(table_thumb_base)
    print "\nTop 20 base address candidates from ARM&THUMB:"
    for score in sorted(merge_table.items(), key=lambda d: d[1], reverse=True)[:20]:
        print "0x%x\t%d" % score

    sys.exit(0)

packetsize = 1024 * 1024
def get_pointers(f, size):
    table = set([])
    tbladd = table.add
    f.seek(0)
    data = f.read(size)
    offset = 0
    count_ptr = 0
    while offset < size:
        if ord(data[offset + 2]) == 0x9F and ord(data[offset + 3]) == 0xE5:
            pc = offset + 8
            count_ptr = count_ptr + 1
            imml2 = (ord(data[offset])) + (ord(data[offset + 1]) & 0x0f)
            # rd = ord(data[offset + 1]) & 0xf0
            address = (pc & 0xfffffffc) + imml2
            buf = data[address:address+4]
            rd = struct.unpack("<L", buf)[0]
            tbladd(rd)
        offset += 4
    print "Total ptr found: %d" % count_ptr
    return table


def get_thumb_pointers(f, size):
    table = set([])
    tbladd = table.add
    f.seek(0)
    data = f.read(size)
    offset = 0
    count_ptr = 0
    while offset < size:
        if ord(data[offset + 1]) & 0xf8 == 0x48:
            pc = offset + 4
            count_ptr = count_ptr + 1
            imml2 = ord(data[offset])
            # rd = ord(data[offset + 1]) & 0xf0
            address = (pc & 0xfffffffc) + imml2 * 4
            buf = data[address:address+4]
            rd = struct.unpack("<L", buf)[0]
            tbladd(rd)
        offset += 2
    print "Total thumb_ptr found: %d" % count_ptr
    return table

def get_strings(f, size):
    table = set([])
    tbladd = table.add
    offset = 0
    while True:
        if offset >= size:
            break
        f.seek(offset)
        try:
            data = f.read(20)
        except:
            break
        match = pattern.match(data)
        if match:
            f.seek(offset - 1)
            try:
                char = f.read(1)
            except:
                continue
            if not patternc.match(char):
                tbladd(offset)
                offset += len(match.group(0))
            offset += 20
        else:
            offset += 1
    return table

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    def auto_int(x):
        return int(x, 0)
    parser.add_argument("--min_addr",  type=auto_int, help="start searching at this address", default=0x38000000)
    parser.add_argument("--max_addr",  type=auto_int, help="stop searching at this address",  default=0x38410000)
    parser.add_argument("--page_size", type=auto_int, help="search every this many byte", default=0x1000)
    parser.add_argument("--infile", help="file to scan", default="659-1")
    args = parser.parse_args()

    size = os.path.getsize(args.infile)
    f = open(args.infile, "rb")
    scores = []

    if os.path.exists("str_table.npy"):
        str_table = np.load("str_table.npy")
    else:
        print "Scanning binary for strings..."
        str_table = list(get_strings(f, size))
        str_table.sort()
        np.save("str_table.npy", str_table)
    print "Total strings found: %d" % len(str_table)

    if os.path.exists("ptr_table.npy"):
        ptr_table = np.load("ptr_table.npy")
    else:
        print "Scanning binary for pointers..."
        ptr_table = list(get_pointers(f, size))
        ptr_table.sort(reverse=True)
        np.save("ptr_table.npy", ptr_table)
    print "Total pointers found: %d" % len(ptr_table)

    if os.path.exists("ptr_thumb_table.npy"):
        ptr_thumb_table = np.load("ptr_thumb_table.npy")
    else:
        print "Scanning binary for pointers_thumb..."
        ptr_thumb_table = list(get_thumb_pointers(f, size))
        ptr_thumb_table.sort(reverse=True)
        np.save("ptr_thumb_table.npy", ptr_thumb_table)
    print "Total thumb_pointers found: %d" % len(ptr_thumb_table)


    f.close()
    gc.disable()
    signal.signal(signal.SIGINT, high_scores)

    id = 0
    if os.path.exists("table_base.npy"):
        table_base = np.load("table_base.npy").item()
        id = table_base[-1]
        table_base[-1] = 0
    for idx_s, s in enumerate(str_table):
        if idx_s < id:
            continue
        if idx_s % 1000 == 0 and idx_s != id:
            print "did 1000"
            table_base[-1] = idx_s
            np.save("table_base", table_base)
        for idx_p, p in enumerate(ptr_table):
            base = p - s
            if base < args.min_addr:
                break
            if base % args.page_size == 0 and base >= args.min_addr and base <= args.max_addr:
                print "Trying base address 0x%x" % base
                try:
                    table_base[base] += 1
                except KeyError:
                    table_base[base] = 1
                if table_base[base] > top_score:
                    top_score = table_base[base]
                    print "New highest score, 0x%x: %d" % (base, table_base[base])

    id = 0
    if os.path.exists("table_thumb_base.npy"):
        table_thumb_base = np.load("table_thumb_base.npy").item()
        id = table_thumb_base[-1]
        table_thumb_base[-1] = 0
    for idx_s, s in enumerate(str_table):
        if idx_s < id:
            continue
        if idx_s % 1000 == 0 and idx_s != id:
            print "did 1000"
            table_thumb_base[-1] = idx_s
            np.save("table_thumb_base", table_thumb_base)
        for idx_p, p in enumerate(ptr_thumb_table):
            base = p - s
            if base < args.min_addr:
                break
            if base % args.page_size == 0 and base >= args.min_addr and base <= args.max_addr:
                print "Trying base address 0x%x" % base
                try:
                    table_thumb_base[base] += 1
                except KeyError:
                    table_thumb_base[base] = 1
                if table_thumb_base[base] > top_score_thumb:
                    top_score_thumb = table_thumb_base[base]
                    print "New highest score from thumb, 0x%x: %d" % (base, table_thumb_base[base])




    high_scores(0, 0)