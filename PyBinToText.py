__author__ = 'Shai Shabtai. 2015 (c)'

from BinaryReader import *

BYTE_ORDER     = '=' # Native.
CSV_BSV_FORMAT = 'BSV'

BinToText('Header1.h', 'MyStruct').\
    parse_bin_to_text('MyStruct_Values.bin', BYTE_ORDER, 'MyStruct_Values', CSV_BSV_FORMAT)

print 'Finish decoding.'
