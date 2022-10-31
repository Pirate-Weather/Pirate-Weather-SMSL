#  pywgrib2 5/2020 public domain Wesley Ebisuzaki
#
# provides a simple python interface for reading/writing grib for python based 
# on the fortran wgrib2api
#
#   requirements: python 3.6, numpy (common but not standard), 
#     ctypes and os.path from the standard library

from ctypes import *
import os
import numpy

# load gomp (gnu openmp), gfortran (gnu: IPOLATES, ftp_api), mvec (debian) and 
# wgrib2 libraries, based on your system, run lld wgrib2/wgrib2

# gomp = CDLL("/usr/lib/x86_64-linux-gnu/libgomp.so.1", mode=RTLD_GLOBAL)
# print("loaded gomp library")
# gfortran = CDLL("/lib/x86_64-linux-gnu/libgfortran.so.5", mode=RTLD_GLOBAL)
# print("loaded gfortran library")
# libmvec is needed for ubuntu
# mvec = CDLL("/lib/x86_64-linux-gnu/libmvec.so.1", mode=RTLD_GLOBAL)
# print("loaded mvec library")

# libwgrib2.so must be in same dir as this file, can be link to file
dir=os.path.dirname(__file__)
lib=os.path.join(dir,'libwgrib2.so')

try:
    my_wgrib2=CDLL(lib)
except Exception as e:
    print("*** Problem ",e)
    print("*** Will load wgrib2 library in RTLD_LAZY mode")
    my_wgrib2=CDLL(lib, mode=os.RTLD_LAZY)

print("finished loading libraries")

# default global variables

nx = 0
ny = 0
ndata = 0
nmatch = 0
msgno = 0
submsgno = 0
data = None
lat = None
lon = None
matched = []
grid_defn = []
use_numpy_nan = True
# UNDEFINED values from wgrib2.h
UNDEFINED = 9.999e20
UNDEFINED_LOW = 9.9989e20
UNDEFINED_HIGH = 9.9991e20

debug = False
__version__='0.0.8'
print("pywgrib2_s v"+__version__+" 10-19-2020 w. ebisuzaki")


def wgrib2(arg):
    #
    #    call wgrib2
    #        ex.  pywgrib2.wgrib2(["in.grb","-inv","@mem.0"])
    #
    #    uses C calling convention: 1st arg is name of program
    #
    global debug
    arg_length = len(arg) + 1
    select_type = (c_char_p * arg_length)
    select = select_type()
    item = "pywgrib2"
    select[0] = item.encode('utf-8')

    for key, item in enumerate(arg):
        select[key + 1] = item.encode('utf-8')

    if debug: print("wgrib2 args: ", arg)
    err = my_wgrib2.wgrib2(arg_length, select)
    if debug: print("wgrib2 err=", err)
    return err


def mk_inv(grb_file, inv_file, Use_ncep_table=False, Short=False):
    #
    # make inventory by -Match_inv or -S
    #
    global debug
    cmds = [grb_file, "-rewind_init", grb_file, "-inv", inv_file]

    if Use_ncep_table:
        cmds.append('-set')
        cmds.append('center')
        cmds.append('7')

    if Short == False:
        cmds.append('-Match_inv')
    else:
        cmds.append('-S')

    err = wgrib2(cmds)
    if debug: print("mk_inv: err=", err)
    return err


def close(file):
    #
    # close file, does a flush and frees resources
    #
    global debug
    # create byte object
    a = file.encode('utf-8')
    err = my_wgrib2.wgrib2_free_file(a)
    if debug: print("close error=", err)
    return err


# inq
#
#  data access options
#    1)  select != '' .. N(.m):byte_location only N is not used
#        a field is selected
#    2)  inv, optional match terms
#    3)  inv == FALSE, optional match terms
#
# register and memory files used by inq()
#
# @mem:10 - used by ftp_api_fn0
# @mem:11 - used by matched inv
# @mem:12 - used by grid metadata
# reg_13  - data (data point values)
# reg_14  - lon
# reg_15  - lat


def inq(gfile,
        *matches,
        inv='',
        select='',
        Data=False,
        Latlon=False,
        Regex=False,
        grib='',
        Append_grib=False,
        bin='',
        Append_bin=False,
        Matched=False,
        Grid_defn=False,
        sequential=-1,
        var='',
        time0=None,
        ftime='',
        level=''):

    # based on grb2_inq() from ftn wgrib2api

    global nx, ny, ndata, nmatch, msgno, submsgno, matched
    global data, lat, lon, grid_defn
    global use_numpy_nan, UNDEFINED_LOW, UNDEFINED_HIGH, debug

    data = None
    lat = None
    lon = None
    grid_defn = []
    matched = []

    # how to match

    if inv == '':  # no inventory
        if Regex == False:
            match_option = '-match_fs'
        else:
            match_option = '-match'
    else:  # use inventory
        if Regex == False:
            match_option = '-fgrep'
        else:
            match_option = '-egrep'

    if select != '':  # selected field, use -d, sequential not valid
        if Matched != False:
            cmds = [
                gfile, "-d", select, "-last", "@mem:11", "-print_out", ":",
                "@mem:11", "-S", "-last", "@mem:11", "-nl_out", "@mem:11",
                "-ftn_api_fn0", "-last0", "@mem:10", "-inv", "/dev/null"
            ]
        else:
            cmds = [
                gfile, "-d", select, "-ftn_api_fn0", "-last0", "@mem:10",
                "-inv", "/dev/null"
            ]

    elif inv != '':  # use inventory
        if Matched != False:
            cmds = [
                gfile, "-i_file", inv, "-last", "@mem:11", "-ftn_api_fn0",
                "-last0", "@mem:10", "-inv", "/dev/null", "-print_out", ":",
                "@mem:11", "-S", "-last", "@mem:11", "-nl_out", "@mem:11"
            ]
        else:
            cmds = [
                gfile, "-i_file", inv, "-ftn_api_fn0", "-last0", "@mem:10",
                "-inv", "/dev/null"
            ]
        if sequential <= 0:
            cmds.append('-rewind_init')
            cmds.append(inv)
        if sequential >= 0:
            cmds.append('-end')
        for m in matches:
            cmds.append(match_option)
            cmds.append(m)
    else:  # no inventory
        if Matched != False:
            cmds = [
                gfile, "-last", "@mem:11", "-ftn_api_fn0", "-last0", "@mem:10",
                "-inv", "/dev/null", "-print_out", ":",
                "@mem:11", "-S", "-last", "@mem:11", "-nl_out", "@mem:11"
            ]
        else:
            cmds = [
                gfile, "-ftn_api_fn0", "-last0", "@mem:10", "-inv", "/dev/null"
            ]
        if sequential <= 0:
            cmds.append('-rewind_init')
            cmds.append(gfile)
        if sequential >= 0:
            cmds.append('-end')
        for m in matches:
            cmds.append(match_option)
            cmds.append(m)

    if var != '':
        cmds.append(match_option)
        cmds.append(':' + var + ':')

    if time0 is not None:
        if time0 < 0:
            return -1
        cmds.append(match_option)
        if time0 <= 9999999999:
            cmds.append(':d=' + str(time0) + ':')
        else:
            cmds.append(':D=' + str(time0) + ':')

    if ftime != '':
        cmds.append(match_option)
        cmds.append(':' + ftime + ':')

    if level != '':
        cmds.append(match_option)
        cmds.append(':' + level + ':')

    if grib != '':
        if Append_grib != False:
           cmds.append("-append")
        cmds.append("-grib")
        cmds.append(grib)
        if Append_grib != False:
           cmds.append("-no_append")

    if bin != '':
        if Append_bin != False:
           cmds.append("-append")
        cmds.append("-no_header")
        cmds.append("-bin")
        cmds.append(bin)
        if Append_bin != False:
           cmds.append("-no_append")

    if Data != False:
        cmds.append("-rpn")
        cmds.append("sto_13")

    if Latlon != False:
        cmds.append("-rpn")
        cmds.append("rcl_lon:sto_14:rcl_lat:sto_15")

    if Grid_defn != False:
        cmds.append("-one_line")
        cmds.append("-grid")
        cmds.append("-last")
        cmds.append("@mem:12")
        cmds.append("-nl_out")
        cmds.append("@mem:12")

    if debug: print('wgrib2 args=', cmds)
    err = wgrib2(cmds)

    if err > 0:
        if debug: print("wgrib2 failed err=", err)
        nmatch = -1
        return -1

    if mem_size(10) == 0:
        if debug: print("no match")
        nmatch = 0
        return 0

    string = get_str_mem(10)
    x = string.split()
    nmatch = int(x[0])
    ndata = int(x[1])
    nx = int(x[2])
    ny = int(x[3])
    msgno = int(x[4])
    submsgno = int(x[5])
    if (nmatch == 0):
        if debug: print("inq found no matches, program error")
        return 0

# for weird grids nx=-1/0 ny=-1/0
    if (nx * ny != ndata):
        nx = ndata
        ny = 1

    if Grid_defn != False:
        size = my_wgrib2.wgrib2_get_mem_buffer_size(12)
        string = create_string_buffer(size)
        err = my_wgrib2.wgrib2_get_mem_buffer(string, size, 12)
        if debug: print("get_str_mem 12 err=", err)
        if (err == 0):
            grid_defn = string.value.decode("utf-8").rstrip().split('\n')

# get data, lat/lon
    if (Data != False or Latlon != False):
        array_type = (c_float * ndata)
        array = array_type()

        if (Data != False):
            err = my_wgrib2.wgrib2_get_reg_data(byref(array), ndata, 13)
            if (err == 0):
                data = numpy.reshape(numpy.array(array), (nx, ny), order='F')
                if use_numpy_nan:
                    data[numpy.logical_and((data > UNDEFINED_LOW), (data < UNDEFINED_HIGH))] = numpy.nan
        if (Latlon != False):
            err = my_wgrib2.wgrib2_get_reg_data(byref(array), ndata, 14)
            if (err == 0):
                lon = numpy.reshape(numpy.array(array), (nx, ny), order='F')
                if use_numpy_nan:
                    lon[numpy.logical_and((lon > UNDEFINED_LOW), (lon < UNDEFINED_HIGH))] = numpy.nan
            err = my_wgrib2.wgrib2_get_reg_data(byref(array), ndata, 15)
            if (err == 0):
                lat = numpy.reshape(numpy.array(array), (nx, ny), order='F')
                if use_numpy_nan:
                    lat[numpy.logical_and((lat > UNDEFINED_LOW), (lat < UNDEFINED_HIGH))] = numpy.nan

    if Matched != False:
        size = my_wgrib2.wgrib2_get_mem_buffer_size(11)
        string = create_string_buffer(size)
        err = my_wgrib2.wgrib2_get_mem_buffer(string, size, 11)
        if debug: print("get_str_mem err=", err)
        if (err == 0):
            matched = string.value.decode("utf-8").rstrip().split('\n')

    if debug:
        print("inq nmatch=", nmatch)
        print("ndata=", ndata, nx, ny)
        print("msg=", msgno, submsgno)
        print("has_data=", data is not None)
    return nmatch

#
# write grib message
#   returns string of metadata (-S)
#   '' for error
#
def write(gfile,
          template,
          msgno,
          new_data=None,
          Append=False,
          var='',
          lev='',
          time0=None,
          ftime='',
          packing='',
          d_scale=None,
          b_scale=None,
          encode_bits=None,
          metadata='',):
    #
    # write grib message (record)
    #
    global use_numpy_nan, UNDEFINED, debug

#   if you only change metadata, no need to pack grid point data
    pack = False

    cmds = [
        template, "-rewind_init", template, "-d",
        str(msgno), "-inv", "@mem:11"
    ]

    # metadata is first source, var, lev are applied afterwards
    if metadata != '':
        cmds.append("-set_metadata_str")
        cmds.append(metadata)

    if time0 is not None:
        cmds.append("-set_date")
        cmds.append(str(time0))

    if var != '':
        cmds.append("-set_var")
        cmds.append(var)

    if lev != '':
        cmds.append("-set_lev")
        cmds.append(lev)

    if ftime != '':
        cmds.append("-set_ftime")
        cmds.append(ftime)

    if packing != '':
        cmds.append("-set_grib_type")
        cmds.append(packing)
        pack = True

    # set grid point data
    # -rpn will clear scaling parameters, so set grid point data first
    
    if new_data is not None:
        asize = new_data.size
        a = new_data.astype(dtype=numpy.float32).reshape((asize),order='F')
        if use_numpy_nan:
            a[numpy.isnan(a)] = UNDEFINED
        a_p = a.ctypes.data_as(c_void_p)
        err = my_wgrib2.wgrib2_set_reg(a_p, asize, 10)
        cmds.append("-rpn")
        cmds.append("rcl_10")
        pack = True

    if d_scale == "same" or b_scale == "same":
        cmds.append("-set_grib_max_bits")
        cmds.append("24")
        cmds.append("-set_scaling")
        cmds.append("same")
        cmds.append("same")
        pack = True
    elif d_scale is not None or b_scale is not None:
        if d_scale is None:
            d_scale = 0
        if b_scale is None:
            b_scale = 0
        cmds.append("-set_grib_max_bits")
        cmds.append("24")
        cmds.append("-set_scaling")
        cmds.append(str(d_scale))
        cmds.append(str(b_scale))
        pack = True

    if encode_bits is not None:
        cmds.append("-set_grib_max_bits")
        cmds.append("24")
        cmds.append("-set_bin_prec")
        cmds.append(str(encode_bits))
        pack = True

#     Write out grib message

    if Append != False:
        cmds.append("-append")
    if pack == False:
        cmds.append("-grib")
    else:
        cmds.append("-grib_out")
    cmds.append(gfile)

    cmds.append("-S")

    #
    err = wgrib2(cmds)
    if debug: print("write: err=", err)
    if err != 0:
        return None
    size = my_wgrib2.wgrib2_get_mem_buffer_size(11)
    string = create_string_buffer(size)
    err = my_wgrib2.wgrib2_get_mem_buffer(string, size, 11)
    if debug: print("get_str_mem err=", err)
    if (err != 0):
        return None
    else:
        return string.value.decode("utf-8").rstrip()


def read_inv(file):
    #
    # read inventory from memory or regular file
    # returns the inventory as a list
    #
    global debug
    if file[0:5] == '@mem:':
        i = int(file[5:])
        a = get_str_mem(i)
    else:
        close(file)
        f = open(file, 'r')
        a = f.read()
        f.close()

    if a == '':
        return []
    s = a.rstrip().split('\n')
    return s

#
# get the version of wgrib2 and configuration functions
#

def wgrib2_version():
    err = wgrib2(['-inv', '@mem:10','-version'])
    size = my_wgrib2.wgrib2_get_mem_buffer_size(10)
    string = create_string_buffer(size)
    err = my_wgrib2.wgrib2_get_mem_buffer(string, size, 10)
    s = string.value.decode("utf-8")
    return s

def wgrib2_config():
    err = wgrib2(['-inv', '@mem:10','-config'])
    size = my_wgrib2.wgrib2_get_mem_buffer_size(10)
    string = create_string_buffer(size)
    err = my_wgrib2.wgrib2_get_mem_buffer(string, size, 10)
    s = string.value.decode("utf-8")
    s = s.rstrip().split('\n')
    return s

#
# These are low level api functions
#


def mem_size(arg):
    #
    #     return size of @mem:arg
    #
    global debug
    i = c_int(arg)
    size = my_wgrib2.wgrib2_get_mem_buffer_size(i)
    if debug: print("mem_size=", size)
    return size


def get_str_mem(arg):
    #
    #    return a string of contents of @mem:arg
    #
    global debug
    i = c_int(arg)
    size = my_wgrib2.wgrib2_get_mem_buffer_size(i)
    string = create_string_buffer(size)
    err = my_wgrib2.wgrib2_get_mem_buffer(string, size, i)
    if debug: print("get_str_mem err=", err)
    s = string.value.decode("utf-8")
    return s

def get_bytes_mem(arg):
    #
    #    return bytes with contents of @mem:arg
    #
    global debug
    i = c_int(arg)
    size = my_wgrib2.wgrib2_get_mem_buffer_size(i)
    if debug: print("get_bytes_mem: size=",size)
    array = create_string_buffer(size)
    err = my_wgrib2.wgrib2_get_mem_buffer(array, size, i)
    if debug: print("get_byte_mem err=", err)
    return array

def get_flt_mem(mem_no):
    # return contents of mem file as numpy array (vector)
    global debug
    i = c_int(mem_no)
    size = my_wgrib2.wgrib2_get_mem_buffer_size(i)
    if (size % 4) != 0:
        if debug:
            print("*** ERROR: get_flt_mem, not float @mem",mem_no)
        return None
    size_flt = int(size / 4)
    array_type = (c_float * size_flt)
    array = array_type()
    err = my_wgrib2.wgrib2_get_mem_buffer(byref(array), size, i)
    if err != 0:
        if debug:
            print("*** ERROR: get_flt_mem, could not read @mem",mem_no)
        return None
    data = numpy.array(array)
    if use_numpy_nan:
        data[numpy.logical_and((data > UNDEFINED_LOW), (data < UNDEFINED_HIGH))] = numpy.nan

    return data


def set_mem(mem_no,data):
    global debug, use_numpy_nan
    i = c_int(mem_no)

    # data can be type bytes, str or something else in future
    if isinstance(data,bytes):
        size = c_int(len(data))
        err = my_wgrib2.wgrib2_set_mem_buffer(data, size, i)
    elif isinstance(data[0],bytes):
        size = c_int(len(data))
        err = my_wgrib2.wgrib2_set_mem_buffer(data, size, i)
    elif isinstance(data, str):
        size = c_int(len(data))
        a = data.encode('utf-8')
        err = my_wgrib2.wgrib2_set_mem_buffer(a, size, i)
    elif isinstance(data, numpy.ndarray):
        asize = data.size
        size = c_int(4*asize)
        a = data.astype(dtype=numpy.float32).reshape(asize)
        if use_numpy_nan:
            a[numpy.isnan(a)] = UNDEFINED
        a_p = a.ctypes.data_as(c_void_p)
        err = my_wgrib2.wgrib2_set_mem_buffer(a_p, size, i)
    else:
        print("set_mem does not support ",type(data))
        quit()

    if (debug):
        print("set_mem: err=", err)
    return err

#
#  register routines
#


def reg_size(regno):
    # return size of register-arg
    global debug
    i = c_int(regno)
    size = my_wgrib2.wgrib2_get_reg_size(i)
    if debug: print("reg_size=", size)
    return size

def get_reg(regno):
    # return register(arg) as numpy array (vector)
    #
    # get size of register
    #
    global use_numpy_nan, debug
    i = c_int(regno)
    size = my_wgrib2.wgrib2_get_reg_size(i)
    array_type = (c_float * size)
    array = array_type()
    err = my_wgrib2.wgrib2_get_reg_data(byref(array), size, i)
    if err != 0:
       if debug: print("get_reg wgrib2 err=", err)
       return None
    # don't know dimensions of register
    data = numpy.array(array)
    if use_numpy_nan:
        data[numpy.logical_and((data > UNDEFINED_LOW), (data < UNDEFINED_HIGH))] = numpy.nan
    return data

def set_reg(regno, array):
    #
    # set register(regno) = array
    #
    global use_numpy_nan, debug
    i = c_int(regno)
    asize = array.size

    # convert array to 32-bit float, linear
    a = array.astype(dtype=numpy.float32).reshape((asize))
    if use_numpy_nan:
        a[numpy.isnan(a)] = UNDEFINED
    a_p = a.ctypes.data_as(c_void_p)

    err = my_wgrib2.wgrib2_set_reg(a_p, asize, i)
    if debug: print("set_reg err=", err)
    return err
