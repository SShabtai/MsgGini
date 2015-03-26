__author__ = 'Shai Shabtai, 2015 (c)'

# Translate a C base struct into python's format characters.
# The format characters string can be used to translate a binary representation to an ASCII CSV representation.
# The format characters string can also be used to translate back an ASCII CSV to binary buffer and then
# be store or send over communication channel as part of a message generator application.
# This class is utilizing the CppHeaderParser open source and free library to parse the CPP header and
# the BinaryReader class to convert it's tags to format characters.

# TODO: Open files from a given path (e.g., ../includes)
# TODO: Remove "WARN-enum: nameless enum"
# TODO: Replace with define: typedef unsigned short UShort;
# TODO: Add base types:
"""
#define T_REAL32 float
#define T_REAL64 double
#define T_SINT int
#define USHORT unsigned short
#define UShort unsigned short
#define UINT unsigned int
#define T_UINT unsigned int
#define T_REAL float
#define DOUBLE double
#define Double double
#define Ulong unsigned long
#define Uint unsigned int
#define Int int
"""

import struct
import CppHeaderParser
import re
import os
from struct import *

# Constants:
PRINT_DEBUG_INFO = False

class BinaryReaderEOFException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return 'Not enough bytes in file to satisfy read request'

class BinaryReader:
    # Map well-known type names into struct format characters.
    typeNames = {
        'char': 'c',
        'TChar': 'c',
        'TSInt8': 'c',
        'T_CHAR': 'c',
        'signed char': 'b',
        'int8': 'b',
        'T_SINT8': 'b',
        'T_BOOL': 'b',
        'unsigned char': 'B',
        'uint8': 'B',
        'TUInt8': 'B',
        'T_UINT8': 'B',
        'bool': '?',
        'Bool': '?',
        'BOOL': '?',
        'TBool': '?',
        'short': 'h',
        'int16': 'h',
        'TSInt16': 'h',
        'T_SINT16': 'h',
        'unsigned short': 'H',
        'uint16': 'H',
        'TUInt16': 'H',
        'USHORT': 'H',
        'T_UINT16': 'H',
        'int': 'i',
        'int32': 'i',
        'TSInt': 'i',
        'T_SINT': 'i',
        'unsigned int': 'I',
        'uint32': 'I',
        'UINT': 'I',
        'long': 'l',
        'T_SLONG': 'l',
        'T_SINT32': 'l',
        'TUInt': 'I',
        'TSLong': 'I',
        'TSInt32': 'I',
        'T_UINT': 'I',
        'unsigned long': 'L',
        'TULong': 'L',
        'TUInt32': 'L',
        'T_ULONG': 'L',
        'T_UINT32': 'L',
        'long long': 'q',
        'int64': 'q',
        '__int64': 'q',
        'unsigned long long': 'Q',
        'uint64': 'Q',
        'char[]': 's',
        'void *': 'P',
        'float': 'f',
        'TReal32': 'f',
        'T_REAL32': 'f',
        'double': 'd',
        'TReal64': 'd',
        'T_REAL64': 'd',
        'T_UINT64': 'd',
        'T_SINT64': 'd',
        'char[]': 's'}

    def __init__(self, fileName):
        self.file = open(fileName, 'rb')

    def read(self, typeName):
        typeFormat = BinaryReader.typeNames[typeName.lower()]
        typeSize = struct.calcsize(typeFormat)
        value = self.file.read(typeSize)
        if typeSize != len(value):
            raise BinaryReaderEOFException
        return struct.unpack(typeFormat, value)[0]

    def __del__(self):
        self.file.close()

class HeadersFormatChars:
    def __init__(self, h_file_name, cpp_struct_name):
        self.__h_file_path, self.__h_file_name = os.path.split(h_file_name)
        self.__cpp_struct_name = cpp_struct_name
        self.py_fmt_chars_str = '' # output
        self.__header_names_list = [] # output
        self.__cppHeader = None
        self.__h_file_data = ''
        self.__type_counter = 0
        pattern_const_to_def = r'(.*?)(\w*) *?=(.*\d);' # 'static const unsigned short MAX_ESTIMATION_REPLIES = 20;'
        pattern_const_brackets_to_def = r'(.*?)(\w*?)\((.*)\);' # const T_REAL32 DEG2RAD(0.017453292519943f);
        self.__pattern_obj_const_to_def = re.compile(pattern_const_to_def, re.MULTILINE)
        self.__pattern_obj_const_brackets_to_def = re.compile(pattern_const_brackets_to_def, re.MULTILINE)

    def __is_h_file_parsed(self, header_file_name, include_list):
        for name in include_list:
            name = name.strip("\"")
            if name == header_file_name:
                return True
        return False

    def __convert_const_to_def(self, file_data_str):
        # replacement_string = "#define" + "\\0" + "\\2" + "\\3"
        # replacement_string = "#define".rstrip(' \t\r\n\0') + "\\0 " + "\\2 " + " =" + "\\3" + ';'
        replacement_string = "#define " + "\\0 " + "\\2 " + " =" + "\\3" + ';' #TODO: Remove NUL from: #define NUL TOM_ICD_VER_MAJOR  = 1;
        file_data_str_no_bkts = self.__pattern_obj_const_brackets_to_def.sub(replacement_string, file_data_str)
        return self.__pattern_obj_const_to_def.sub(replacement_string, file_data_str_no_bkts)

    def __append_cpp_header_data(self, new_cpp_header_data):
        try:
            if None == self.__cppHeader:
                self.__cppHeader = new_cpp_header_data
            else:
                self.__cppHeader.defines += new_cpp_header_data.defines
                self.__cppHeader.enums += new_cpp_header_data.enums
                self.__cppHeader.includes += new_cpp_header_data.includes
                self.__cppHeader.structs = dict( list(self.__cppHeader.structs.items()) + list(new_cpp_header_data.structs.items()))
                self.__cppHeader.classes = dict( list(self.__cppHeader.classes.items()) + list(new_cpp_header_data.classes.items()))
        except:
            print 'Error: Append cpp header data.'
            exit(1)

    def __read_h_file_content(self, h_name):
        try:
            f = open(h_name)
            h_file_data = f.read()
            if not h_file_data:
                print h_name, 'is empty.'
            no_struct_typedef_file_data = self.__remove_struct_type_defs(h_file_data)
            no_enums_typedef_file_data  = self.__remove_enum_type_defs(no_struct_typedef_file_data)
            no_cmnts_file_data          = self.__remove_c_comments(no_enums_typedef_file_data)
            consts_as_defines           = self.__convert_const_to_def(no_cmnts_file_data)
            # print consts_as_defines
            try:
                ######### DEBUG ##############
                # print consts_as_defines
                # try:
                #     tmp_h_file = open('tmp_h.h', 'a')
                #     tmp_h_file.write(consts_as_defines)
                #     tmp_h_file.close()
                #     print 'Dedug file written.'
                # except IOError as e:
                #     print 'Error: Cannot open output text file:', e
                #     sys.exit(1)
                # cppHeader = CppHeaderParser.CppHeader('tmp_h.h')
                ######### DEBUG ##############
                cppHeader = CppHeaderParser.CppHeader(consts_as_defines, 'string')
                # print cppHeader
                self.__append_cpp_header_data(cppHeader)
            except CppHeaderParser.CppParseError as e:
                print(e)
                sys.exit(1)
            f.close()
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror), ':', h_name
            return False
        except:
            print "Read file unexpected error:", h_name
            # raise
            return False
        return True

    def __parse_h_data(self, main_h_name, parsed_incl):
        # h_name = main_h_name.strip("\"")
        h_name1 = main_h_name.replace('"','').strip()
        h_name2 = h_name1.replace('<','').strip()
        h_name = h_name2.replace('>','').strip()
        if not self.__is_h_file_parsed(h_name, parsed_incl):
            if os.path.exists(h_name):
                if os.path.isfile(h_name):
                    if PRINT_DEBUG_INFO:
                        print 'parsing:', h_name
                    if not self.__read_h_file_content(h_name):
                        print 'error parsing:', h_name
                else:
                    print 'error:', h_name, 'isn''t a file.'
                for incl in CppHeaderParser.CppHeader(h_name).includes:
                    no_cmnts_incl = self.__remove_c_comments(incl)
                    parsed_incl.append(h_name)
                    self.__parse_h_data(no_cmnts_incl, parsed_incl)
            else:
                if PRINT_DEBUG_INFO:
                    print 'Error:', h_name, 'does not exists in:', os.getcwd() # Change to self.__h_file_path
                pass # Some h files might not exists.
            parsed_incl.append(h_name)

    def __remove_struct_type_defs(self, h_file_data):
        if h_file_data.find("typedef"): # TODO: replace with regex.
            # Allow space (\s) or no space (*) before typedef and any space or tab before the struct string.
            return re.sub(r'\s*typedef(\s*struct+)', "\n\nstruct", h_file_data)
        else:
            return h_file_data

    def __remove_enum_type_defs(self, h_file_data):
        # Allow space (\s) or no space (*) before typedef and any space or tab before the enum string.
        h_clean_file_data = re.sub(r'\s*typedef(\s*enum+)', "\n\nenum", h_file_data)
        return h_clean_file_data

    def __remove_c_comments(self, h_file_data):
        """Remove C-style /*comments*/ from a string."""
        p = r'/\*[^*]*\*+([^/*][^*]*\*+)*/|("(\\.|[^"\\])*"|\'(\\.|[^\'\\])*\'|.[^/"\'\\]*)'
        return ''.join(m.group(2) for m in re.finditer(p, h_file_data, re.M|re.S) if m.group(2))

    def __get_fundamental_type_from_define(self, define_type):
        for define in self.__cppHeader.defines:
            # if 0 == define.find(define_type):
            def_line_list = define.split()
            if define_type == def_line_list[0]:
                if 2 < len(def_line_list): # Support "unsigned short"
                    base_define = ' '.join(def_line_list[1:]) # Two list strings to one.
                else:
                    base_define = def_line_list[1]
                if base_define in BinaryReader.typeNames:
                    # print base_define, 'is in typeNames'
                    return base_define
                else:
                    # print define.split()[1], 'isn''t in typeNames'
                    return None

    def __get_array_size_from_define(self, define_type):
        for define in self.__cppHeader.defines:
            if define.find(define_type):
                # print define
                search_results = re.search(r'(.*?)(\w*)' + define_type + r' *?=(.*\d);', define)
                if search_results:
                    if search_results.groups > 2:
                        # print 'Define:', define_type, 'size:', int(search_results.group(3))
                        return int(search_results.group(3))
        return None

    def __is_an_enum(self, data_type):
        for enum in self.__cppHeader.enums:
            try:
                if enum['name'] == data_type:
                    return True
            except:
                pass
        return False

    def __is_a_struct(self, struct_name):
        for cls in self.__cppHeader.classes:
            if cls == struct_name:
                return True
        return False

    def __handle_single_type(self, attrib):
        name_space = re.search(r'::', attrib["type"])
        if name_space:
            attrib_type = attrib["type"].split("::")[1]
            if PRINT_DEBUG_INFO:
                print "Removing namespace:", attrib["type"].split("::")[0]
        else:
            attrib_type = attrib["type"]
        fund_type = self.__get_fundamental_type_from_define(attrib_type)
        if fund_type:
            if PRINT_DEBUG_INFO:
                print attrib["name"], 'type', attrib_type, 'type-format', BinaryReader.typeNames[str(fund_type)]
            self.py_fmt_chars_str += BinaryReader.typeNames[fund_type] + ' '
            self.__type_counter += 1
        else:
            if self.__is_a_struct(attrib_type):
                self.__struct_walk(attrib_type)
            else:
                if self.__is_an_enum(attrib_type):
                    if PRINT_DEBUG_INFO:
                        print attrib["name"], 'type', attrib_type, 'is enum', \
                            'type-format', BinaryReader.typeNames['int']
                    self.py_fmt_chars_str += BinaryReader.typeNames['int'] + ' '
                    self.__type_counter += 1
                else:
                    try:
                        self.py_fmt_chars_str += BinaryReader.typeNames[attrib_type] + ' '
                        self.__type_counter += 1
                        if PRINT_DEBUG_INFO:
                            print attrib["name"], 'type', attrib_type, 'type-format', BinaryReader.typeNames[attrib_type]
                    except:
                        print 'Unknown type:', attrib["type"], 'Struct:', self.__cpp_struct_name, \
                            'Header:', self.__h_file_name, 'Line#:', attrib["line_number"]
                        exit(1) # TODO: Raise exception.

    def __handle_array_type(self, attrib):
        if attrib["array_size"].isdigit():
            array_size = int(attrib["array_size"])
        else:
            tmp = self.__get_array_size_from_define(attrib["array_size"])
            if None == tmp:
                print 'Unknown array size of type:', attrib["type"], 'Struct:', self.__cpp_struct_name, \
                    'Size:', attrib["array_size"], 'Header:', self.__h_file_name, 'Line#:', attrib["line_number"]
                exit(1) # TODO: Raise exception.
            else:
                array_size = int(tmp)
        for i in range(array_size):
            self.__handle_single_type(attrib)

    def __struct_walk(self, struct_name):
        for attrib in self.__cppHeader.classes[struct_name]["properties"]["public"]:
            if 1 == attrib['array']:
                self.__handle_array_type(attrib)
            else:
                self.__handle_single_type(attrib)

    def __store_header_list(self, header_list):
        struct_name = ''
        for head_name in header_list:
            if('' == struct_name):
                struct_name = head_name
            else:
                struct_name = struct_name + "." + head_name
        # print struct_name
        self.__header_names_list.append(struct_name)

    # Public methods:
    def parse_struct(self):
        self.__parse_h_data(self.__h_file_name, [])
        if None == self.__cppHeader:
            exit(1)
        if PRINT_DEBUG_INFO:
            print 'CppHeaderParser lib version:', CppHeaderParser.version
            print self.__cppHeader
        try:
            self.__struct_walk(self.__cpp_struct_name)
        except ValueError as e:
            print(e)
            return ''
            sys.exit(1)
        except:
            print "Error: struct parsing of", self.__cpp_struct_name, 'from', self.__h_file_name
            raise
            return ''
        return self.py_fmt_chars_str, self.__type_counter

    def get_header_names(self, struct_name, header_list):
        for attrib in self.__cppHeader.classes[struct_name]["properties"]["public"]:
            if 1 == attrib['array']:
                if attrib["array_size"].isdigit():
                    array_size = int(attrib["array_size"])
                else:
                    array_size = int(self.__get_array_size_from_define(attrib["array_size"]))
                if array_size:
                    for idx in range(array_size-1):
                        if attrib['fundamental']:
                            header_list.append(attrib["name"] + "(" + str(idx+1) + ")")
                            self.__store_header_list(header_list)
                            header_list.pop()
                        else:
                            header_list.append(attrib["name"])
                            self.get_header_names(attrib["type"], header_list)
                            header_list.pop()
            else:
                if attrib["fundamental"]:
                    if PRINT_DEBUG_INFO:
                        print attrib["name"], 'type', attrib["type"], 'ctypes', attrib["ctypes_type"]
                    header_list.append(attrib["name"])
                    self.__store_header_list(header_list)
                    header_list.pop()
                else:
                    fund_type = self.__get_fundamental_type_from_define(attrib["type"])
                    if not None == fund_type:
                        if PRINT_DEBUG_INFO:
                            print attrib["name"], 'type', attrib["type"]
                        header_list.append(attrib["name"])
                        self.__store_header_list(header_list)
                        header_list.pop()
                    else: # not a special define
                        if self.__is_an_enum(attrib["type"]):
                            if PRINT_DEBUG_INFO:
                                print attrib["name"], 'type', attrib["type"], 'ctypes', attrib["ctypes_type"]
                            header_list.append(attrib["name"])
                            self.__store_header_list(header_list)
                            header_list.pop()
                        else:
                            header_list.append(attrib["name"])
                            try:
                                self.get_header_names(attrib["type"], header_list)
                            except:
                                print 'Unknown type:', attrib["type"], 'Struct:', self.__cpp_struct_name, \
                                    'Header:', self.__h_file_name, 'Line#:', attrib["line_number"]
                                exit(1) # TODO: Raise exception.
                            header_list.pop()

    def get_header_names_list(self):
        return self.__header_names_list

    def __del__(self):
        if PRINT_DEBUG_INFO:
            print 'HeadersFormatChars finished.'
