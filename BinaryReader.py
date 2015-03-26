__author__ = 'Shai Shabtai, 2015 (c)'

# 1. Read and parse the C base header struct data types utilizing the CppHeaderParser lib.
# 2. Translate the data types to python format characters.
# 3. Load the binary file and unpack the data values using the python format characters (struct.unpack)
#    using BinaryReader

#           Byte Order, Size, and Alignment
#
# Character 	Byte order 	            Size 	    Alignment
#   @ 	        native 	                native 	    native
#   = 	        native 	                standard 	none
#   < 	        little-endian 	        standard 	none
#   > 	        big-endian 	            standard 	none
#   ! 	        network (= big-endian) 	standard 	none

from cpp_struct_to_py_fmt_chars import *
from itertools import *
import pandas as pd
import csv
import numpy as np
import time
import socket as cSocket

# Constants:
PRINT_DEBUG_INFO    = False
TYPE_CAST           = False

class BinToText:
    def __init__(self, header_name, struct_name):
        if '' == header_name or '' == struct_name:
            print 'Bad input parameters:', header_name, struct_name
            exit(1)
        self.__h_file_path, self.__h_file_name = os.path.split(header_name)
        self.__cpp_struct_name = struct_name
        self.__header_fmt_chars = HeadersFormatChars(self.__h_file_name, self.__cpp_struct_name)
        self.py_fmt_chars_str, self.py_fmt_chars_count = self.__header_fmt_chars.parse_struct()
        if PRINT_DEBUG_INFO:
            print self.py_fmt_chars_str
        self.py_fmt_chars = self.__remove_space_from_list(self.py_fmt_chars_str)
        self.__header_fmt_chars.get_header_names(self.__cpp_struct_name, [self.__cpp_struct_name])
        self.__header_names_list = self.__header_fmt_chars.get_header_names_list()
        if PRINT_DEBUG_INFO:
            print self.__header_names_list

    def __replace(self, l, X, Y):
        i = 0
        for v in l:
            if str(v) == str(X):
                l.pop(i)
                l.insert(i, Y)
            i += 1

    def __remove_space_from_list(self, chars_list):
        no_spaces_list = []
        for c in chars_list:
            if c.isalpha() or c == '?': # Remove space.
                no_spaces_list.append(c)
        return no_spaces_list

    def __read_bin_file_data(self, bin_file_name):
        if os.path.exists(bin_file_name):
            try:
                f = open(bin_file_name, 'rb')
                bin_file_data = f.read()
                if not bin_file_data:
                    print bin_file_name, 'is empty.'
                    exit(1)
                f.close()
            except IOError as e:
                print "I/O error({0}): {1}".format(e.errno, e.strerror), ':', bin_file_name
                return None
            except:
                print "Read file unexpected error:", sys.exc_info()[0], ':', bin_file_name
                raise
                return None
        else:
            print bin_file_name, 'dosn''t exists in path:', os.getcwd()
            exit(1)
        return bin_file_data

    def __write_header_names(self, output_file, output_type):
        if '' == self.__header_names_list or None == self.__header_names_list:
            return False
        if None == output_file:
            return False

        if 'BSV' == output_type:
            # writer = csv.writer(output_file, dialect='excel-tab', lineterminator='\r\n')
            writer = csv.writer(output_file, dialect='excel-tab', lineterminator='\r')
        else:
            if 'CSV' == output_type:
                # writer = csv.writer(output_file, lineterminator='\r\n')
                writer = csv.writer(output_file, lineterminator='\r')

        writer.writerow(self.__header_names_list)

    def __write_msg_values(self, output_file, output_type, msg_values):
        if None == output_file:
            return False
        value_list = []
        lst = list(msg_values)
        self.__replace(lst, 'True', '1')   # Matlab (MathAnalayser) prefers 1 for True
        self.__replace(lst, 'False', '0')  # Matlab prefers 0 for False
        values = tuple(lst)
        # print values
        for value in values:
            if 'BSV' == output_type:
                value_list.append(str(value) + "\t")
            else:
                if 'CSV' == output_type:
                    value_list.append(str(value) + ",")
        output_file.writelines(value_list)
        # output_file.write("\r\n")
        output_file.write("\r")

    def __read_bsv(self, path):
        data_frame = pd.read_csv(path ,sep='\t')
        mtx = data_frame.values # To a matrix
        return mtx

    def __clean_bsv(self, bsv_name, num_of_clms):
        data_frame = pd.read_csv(bsv_name ,sep='\t')
        mtx = data_frame.values
        cleaned_mtx = []
        print mtx
        for msg in mtx:
            values = []
            i = 0
            for value in msg:
                i += 1
                if i > num_of_clms:
                    values.append(value)
            cleaned_mtx.append(values)
        return cleaned_mtx

    # Public methods:
    def get_header_names_list(self):
        return self.__header_names_list

    def get_py_fmt_chars_str(self):
        return self.py_fmt_chars_str

    def parse_bin_to_text(self, bin_file_name, byte_order, output_file_name, output_type):
        if '' == bin_file_name or '' == byte_order or '' == output_file_name:
            print 'Bad input parameters:', bin_file_name, byte_order, output_file_name
            return False
        if (not 'BSV' == output_type) and (not 'CSV' == output_type):
            print 'Bad input parameter:', output_type
            return False
        assert isinstance(self.py_fmt_chars_str, str)
        if '' == self.py_fmt_chars_str:
            return False

        if 'BSV' == output_type:
            output_file_name += '.bsv'
        else:
            if 'CSV' == output_type:
                output_file_name += '.csv'

        bin_data = self.__read_bin_file_data(bin_file_name)
        if None == bin_data:
            return False

        try:
            packer = struct.Struct(byte_order+self.py_fmt_chars_str)

            try:
                out_text_file = open(output_file_name, 'w')
            except IOError as e:
                print 'Error: Cannot open output text file:', output_file_name, e
                sys.exit(1)

            wrote_csv_header = False
            for msg_idx in range(len(bin_data) / packer.size):
                t1 = time.clock()
                msg_data = bin_data[(msg_idx*packer.size):((msg_idx+1)*packer.size)]
                if packer.size == len(msg_data):
                    values = packer.unpack(msg_data)
                    if '' == values or None == values:
                        return False
                    # if not len(values) == len(self.py_fmt_chars_str):
                    #     print 'Error: Message values length is incompatible with header names list length.', \
                    #         len(values), len(self.py_fmt_chars_str), self.__cpp_struct_name
                    #     # print self.py_fmt_chars_str
                    #     # print values
                    #     return False
                    if PRINT_DEBUG_INFO:
                        print msg_idx+1, 'Unpack values:', values
                        print 'Packer total size:', packer.size, 'bytes.', 'Elements:', self.py_fmt_chars_count, \
                            'chars length', len(self.py_fmt_chars), 'Binary data length:', len(msg_data), 'bytes.'
                    if not wrote_csv_header:
                        self.__write_header_names(out_text_file, output_type)
                        wrote_csv_header = True
                    self.__write_msg_values(out_text_file, output_type, values)
                    if not PRINT_DEBUG_INFO:
                        print 'Parsing message#:', msg_idx+1, 'of struct', self.__cpp_struct_name, 'time', time.clock()-t1, 'sec.'
                else:
                    print 'Error: Packer size is incompatible with message length.', \
                        packer.size, len(msg_data)
                    return False
            print 'Parsed', msg_idx+1, 'messages of', self.__cpp_struct_name, 'struct.'

            try:
                out_text_file.flush()
                out_text_file.close()
            except IOError as e:
                print 'Error: Cannot close output text file:', output_file_name, e
                sys.exit(1)

        except struct.error as e:
            print 'struct.pack error:', e, 'at:', self.__cpp_struct_name
        except:
            print "Unexpected struct.pack error:", self.__cpp_struct_name
            raise
        return True

    def parse_text_to_bin(self, text_file_name, input_type, byte_order, output_file_name):
        if '' == text_file_name or '' == byte_order or '' == output_file_name:
            print 'Bad input parameters:', text_file_name, byte_order, output_file_name
            return False
        if (not 'BSV' == input_type) and (not 'CSV' == input_type):
            print 'Bad input parameter:', input_type
            return False
        assert isinstance(self.py_fmt_chars_str, str)
        if '' == self.py_fmt_chars_str:
            return False
        # Read values from BSV file using pandas to a matrix representation.
        if 'BSV' == input_type:
            df = pd.read_csv(text_file_name, skip_blank_lines=True,delimiter='\t')
        else:
            if 'CSV' == input_type:
                df = pd.read_csv(text_file_name, skip_blank_lines=True)
        if df.empty:
            return False
        values_mtx = df.values
        msg_num = 0
        msg_values = values_mtx[msg_num,:]
        # print msg_values
        try:
            bin_data = ''
            column_idx = 0
            packer = struct.Struct(byte_order+self.py_fmt_chars_str)
            for (c, val) in izip(self.py_fmt_chars, msg_values):
                column_idx += 1
                if TYPE_CAST:
                    dt = np.dtype(c)
                    if PRINT_DEBUG_INFO:
                        print 'value:', val, 'casting to:', dt.type(val), 'data type:', np.dtype(c), ':', c, \
                            'size:', calcsize(c), 'bytes.'
                    bin_data += pack(c, dt.type(val)) # Casting to the struct's data type.
                else:
                    if PRINT_DEBUG_INFO:
                        print 'value:', val, 'data type:', np.dtype(c), ':', c, 'size:', calcsize(c), 'bytes.'
                    bin_data += pack(c, val)
            if PRINT_DEBUG_INFO:
                print 'Packer total size:', packer.size, 'bytes.', 'Elements:', self.py_fmt_chars_count, \
                    'chars length', len(self.py_fmt_chars), 'Binary data length:', len(bin_data), 'bytes.'
            if not packer.size == len(bin_data):
                print 'Wrong packer size or binary file size!'
                return False
        except struct.error as e:
            print 'struct.pack error:', e, ' value=', val, 'data type:', np.dtype(c), ':', c, 'at column:', column_idx, 'in struct:', self.__cpp_struct_name
        except:
            print "Unexpected struct.pack error:", ' value=', val, 'data type:', np.dtype(c), ':', c, 'at column:', column_idx, 'in struct:', self.__cpp_struct_name
            raise
        print 'Parsed message#:', msg_num+1, 'successfully.'
        return True

    def send_text_msgs_via_udp(self, text_file_name, time_to_sleep, input_type, byte_order, svr_ip_address, svr_port_num):
        if '' == text_file_name or '' == byte_order or '' == svr_ip_address or not type(svr_port_num) == int:
                print 'Bad input parameters:', text_file_name, byte_order, svr_ip_address, svr_port_num
                return False
        if (not 'BSV' == input_type) and (not 'CSV' == input_type) and (not 'BSV_HAGAI' == input_type):
            print 'Bad input parameter:', input_type
            return False
        assert isinstance(self.py_fmt_chars_str, str)
        if '' == self.py_fmt_chars_str:
            return False
        # Starting client socket.
        serverAddress = (svr_ip_address, svr_port_num)
        try:
            sock = cSocket.socket(cSocket.AF_INET, cSocket.SOCK_DGRAM)
            print 'starting up\'' + serverAddress[0] +'\' port ' + str(serverAddress[1])
        except cSocket.error, msg:
            print 'Failed to create a socket. Error Code: \'' + str(msg[0]) + '.' +str(msg[1])
            exit()
        try:
            #read c Header file and return the types.
            MyStruct_fmt_chars, count = HeadersFormatChars(self.__h_file_name, self.__cpp_struct_name).parse_struct()
            chars = self.__remove_space_from_list(MyStruct_fmt_chars)

            while True:
                #check file type and create a matrix of it.
                if 'BSV' == input_type:
                    mtx = self.__read_bsv(text_file_name)
                elif 'CSV' == input_type:
                    df = pd.read_csv(text_file_name, skip_blank_lines=True)
                    mtx = df.values # To a matrix
                elif 'BSV_HAGAI' == input_type:
                    mtx = self.__clean_bsv(text_file_name, 2)

                bin_value = ''
                #create for each line in the matrix an array and send it as a binary message.
                for msg in mtx:
                    values = []
                    for value in msg:
                            values.append(value)
                    for (c, val) in izip(chars, values):
                        #print c, val
                        if c == "c":
                            bin_value += pack(byte_order+c, chr(int(val)))
                        else:
                            bin_value += pack(byte_order+c, val)
                    try:
                        sock.sendto(bin_value, serverAddress)
                        print 'Sending : \'' + str(bin_value) + '\''
                        time.sleep(time_to_sleep)
                    except cSocket.error, msg:
                        print 'Sending Failed. Error Code: \'' + str(msg[0]) + '.' +str(msg[1])
                break
        except struct.error as e:
            print e, ':', self.__cpp_struct_name
        except:
            print "Unexpected error:", self.__cpp_struct_name
            raise

