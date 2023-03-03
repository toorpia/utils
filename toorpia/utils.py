import os
import sys
import subprocess
import numpy
from map_inspector.map_inspector import map_inspector
from monitoring_scope.monitoring_scope import monitoring_scope
from numpy import float32
from IPython.display import display, HTML

def __check_rawdata_existence(options):
    if 'rawdata' not in options:
        raise Exception('rawdata is not specified')

    for rawdatafile in options['rawdata'].split():
        if not os.path.exists(rawdatafile):
            raise FileNotFoundError(rawdatafile)
        if not os.access(rawdatafile, os.R_OK):
            raise PermissionError('File not readable: %s' % rawdatafile)
    
def __check_rawdata_type(options):
    # automatically try to detect rawdata type: table (csv format) or sound (wav or csv format)
    rdf = options['rawdata'].split()

    if rdf[0].endswith('.wav') or rdf[0].endswith('.WAV') or rdf[0].endswith('.wav.gz') or rdf[0].endswith('.WAV.gz'):
        options['rawdata_type'] = 'sound'
    elif rdf[0].endswith('.csv') or rdf[0].endswith('.CSV') or rdf[0].endswith('.csv.gz') or rdf[0].endswith('.CSV.gz'):
        if 'rawdata_type' not in options:
            if 'type_weight' in options:
                options['rawdata_type'] = 'table'
            elif 'data_index' in options or 'sampling_rate' in options or 'window_length' in options:
                options['rawdata_type'] = 'sound'
            else:
                raise Exception('rawdata_type is not recognized. Please specify type_weight for table, or specify data_index or sampling_rate or window_length for sound.')
        else: # if rawdata_type is specified, check if it is valid
            if options['rawdata_type'] != 'table' and options['rawdata_type'] != 'sound':
                raise Exception('rawdata_type is not valid: %s' % options['rawdata_type'])
    else:
        raise Exception('rawdata type is not recognized: %s' % rdf[0])
    
def __check_working_dir(options):
    if 'working_dir' not in options:
        options['working_dir'] = "analysis" # set default working directory
    if not os.path.exists(options['working_dir']):
        os.makedirs(options['working_dir'], exist_ok=True)
    if not os.access(options['working_dir'], os.W_OK):
        raise PermissionError('Directory not writable: %s' % options['working_dir'])

def __check_required_options_for_table(options):
    if 'type_weight' not in options:
        raise Exception('exec create_type_weight function first')
    elif not os.path.exists(options['type_weight']):
        raise FileNotFoundError(options['type_weight'])

    if 'window_size' not in options:
        options['window_size'] = 1
    if 'reduce_factor' not in options:
        options['reduce_factor'] = 1

def __check_required_options_for_sound(options):
    if options['rawdata_type'] == 'table':
        raise Exception('rawdata_type is table. nothing to do')

    if options['rawdata'].endswith('.csv') or options['rawdata'].endswith('.CSV') or options['rawdata'].endswith('.csv.gz') or options['rawdata'].endswith('.CSV.gz'):
        if 'data_index' not in options:
            print("data_index is not specified, so set it to 1 (default)")
            options['data_index'] = 1
        if 'sampling_rate' not in options:
            print("sampling_rate is not specified, so set it to 48000 Hz (default)")
            options['sampling_rate'] = 48000
    elif options['rawdata'].endswith('.wav') or options['rawdata'].endswith('.WAV') or options['rawdata'].endswith('.wav.gz') or options['rawdata'].endswith('.WAV.gz'):
        if 'data_index' in options:
            print("data_index is not required for wav data, so data_index key is deleted")
            options.pop('data_index', None) # delete data_index key from options
        if 'sampling_rate' not in options:
            print("sampling_rate is not specified, so set it to 48000 Hz (default)")
            options['sampling_rate'] = 48000

    if 'window_length' not in options:
        print("window_length is not specified, so set it to 65536 (default)")
        options['window_length'] = 65536

    __check_working_dir(options)

def __make_option_str_for_table(options):
    option_str = '-o ' + options['type_weight']
    if 'window_size' in options:
        option_str += ' -ws ' + str(options['window_size'])
    if 'reduce_factor' in options:
        option_str += ' -rf ' + str(options['reduce_factor'])

    return option_str

def __make_option_str_for_sound(options):
    option_str = ''
    if options['rawdata'].endswith('.csv') or options['rawdata'].endswith('.CSV') or options['rawdata'].endswith('.csv.gz') or options['rawdata'].endswith('.CSV.gz'):
        option_str += ' -di ' + str(options['data_index'])

    option_str += ' -wl ' + str(options['window_length'])
    if 'sampling_rate' in options:
        option_str += ' -sr ' + str(options['sampling_rate'])
    
    # if extra options are specified, add them
    if 'high_pass_filter' in options:
        option_str += ' -hp ' + str(options['high_pass_filter'])
    if 'low_pass_filter' in options:
        option_str += ' -lp ' + str(options['low_pass_filter'])
    if 'n_moving_average' in options:
        option_str += ' -nm ' + str(options['n_moving_average'])
    if 'window_function' in options:
        option_str += ' -wf ' + str(options['window_function'])
    if 'segment_overlap_ratio' in options:
        option_str += ' -ol ' + str(options['segment_overlap_ratio'])
    
    return option_str

def __set_output_file_for_basemap(options):
    if 'base_segment' not in options:
        options['base_segment'] = options['working_dir'] + '/segments.csv'

    if 'base_segment_log' not in options:
        options['base_segment_log'] = options['working_dir'] + '/segments.log'

    if 'base_xy' not in options:
        options['base_xy'] = options['working_dir'] + '/xy.dat'

    if 'base_xy_log' not in options:
        options['base_xy_log'] = options['working_dir'] + '/xy.log'

    if 'status_mi' not in options:
        options['status_mi'] = options['working_dir'] + '/status.mi'
        
    for file in [options['base_segment'], options['base_segment_log'], options['base_xy'], options['base_xy_log'], options['status_mi']]:
        dirname = os.path.dirname(file)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

def __check_basemap_existence(options):
    if 'working_dir' not in options:
        raise Exception('working_dir is not specified')
    if not os.access(options['working_dir'], os.R_OK):
        raise PermissionError('Directory not readable: %s' % options['working_dir'])

    if 'base_segment' not in options:
        options['base_segment'] = options['working_dir'] + '/segments.csv'

    if 'base_xy' not in options:
        options['base_xy'] = options['working_dir'] + '/xy.dat'

    if 'status_mi' not in options:
        options['status_mi'] = options['working_dir'] + '/status.mi'
        
    for key in ['base_segment', 'base_xy']:
        if not os.path.exists(options[key]):
            raise FileNotFoundError(options[key])
        if not os.access(options[key], os.R_OK):
            raise PermissionError('File not readable: %s' % options[key])

def __set_output_file_for_addplot(options):
    if 'add_segment' not in options:
        options['add_segment'] = options['working_dir'] + '/segments-add.csv'

    if 'add_segment_log' not in options:
        options['add_segment_log'] = options['working_dir'] + '/segments-add.log'

    if 'add_xy' not in options:
        options['add_xy'] = options['working_dir'] + '/xy-add.dat'

    if 'add_xy_log' not in options:
        options['add_xy_log'] = options['working_dir'] + '/xy-add.log'

    if 'add_status_mi' not in options:
        options['add_status_mi'] = options['working_dir'] + '/status-add.mi'

    if 'status_ms' not in options:
        options['status_ms'] = options['working_dir'] + '/status.ms'

    for file in [options['add_segment'], options['add_segment_log'], options['add_xy'], options['add_xy_log'], options['add_status_mi']]:
        if not os.path.exists(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)

def create_type_weight(options):
    __check_rawdata_existence(options)
    __check_working_dir(options)

    if 'type_weight' not in options:
        options['type_weight'] = options['working_dir'] + '/type_weight.csv'
        options['type_weight_log'] = options['working_dir'] + '/type_weight.log'
    if os.path.exists(options['type_weight']):
        os.remove(options['type_weight'])

    __check_rawdata_type(options)
    
    if options['rawdata_type'] == 'sound':
        raise Exception('rawdata_type is sound, so type_weight is not needed')
    

    rv = subprocess.run(f"mkcsvseg -o {options['type_weight']} {options['rawdata']} 1> /dev/null 2> {options['type_weight_log']}", shell=True)
    if rv.returncode != 0:
        print(f"mkcsvseg command failed.", file=sys.stderr)
        sys.exit(1)

    display(HTML(f"<p>Click link <a href='{options['type_weight']}'>{options['type_weight']}</a> to edit and save it.</p>"))

def create_basemap(options):
    __check_rawdata_existence(options)
    __check_rawdata_type(options)

    if options['rawdata_type'] == 'table':
        __check_required_options_for_table(options) # check if required options are given for table type data
        cmd_str = 'mkcsvseg'
        option_str = __make_option_str_for_table(options)
    elif options['rawdata_type'] == 'sound':
        __check_required_options_for_sound(options) # check if required options are given for sound type data
        cmd_str = 'mkfftseg'
        option_str = __make_option_str_for_sound(options)

    __set_output_file_for_basemap(options)

    rv = subprocess.run(f"{cmd_str} {option_str} {options['rawdata']} 2> {options['base_segment_log']} > {options['base_segment']}", shell=True)
    if rv.returncode != 0:
        print(f"{cmd_str} command failed. see {options['base_segment_log']}", file=sys.stderr)
        sys.exit(1)
    
    if 'multi_filter_option' in options:
        multi_filter(options)

    rv = subprocess.run(f"toorpia -m base {options['base_segment']} 2> {options['base_xy_log']} > {options['base_xy']}", shell=True)
    if rv.returncode != 0:
        print(f"toorpia command failed. see {options['base_xy_log']}", file=sys.stderr)
        sys.exit(1)

    if 'map_inspector' in options and options['map_inspector'] == False:
        None
    else: # default: open map inspector
        options['map_inspector'] = True
        
        if len(options['rawdata'].split()) == 1:
            option_rawcsv_str = options['rawdata']
        else:
            option_rawcsv_str = None

        if 'map_inspector_sharable' in options and options['map_inspector_sharable'] == True:
            map_inspector(options['base_segment'], options['base_xy'], options['status_mi'], sharable=True, working_dir=options['working_dir'], rawcsv=option_rawcsv_str)
        else:
            options['map_inspector_sharable'] = False
            map_inspector(options['base_segment'], options['base_xy'], options['status_mi'], working_dir=options['working_dir'], rawcsv=option_rawcsv_str)
    
    x = []
    y = []
    with open(options['base_xy'], "r") as f:
        for line in f:
            coord = line.rstrip().split()
            x.append(float(coord[0]))
            y.append(float(coord[1]))
    return numpy.array(x), numpy.array(y)

def open_basemap(options):
    __check_basemap_existence(options)

    if 'map_inspector' in options and options['map_inspector'] == False:
        None
    else:
        options['map_inspector'] = True

        if len(options['rawdata'].split()) == 1:
            option_rawcsv_str = options['rawdata']
        else:
            option_rawcsv_str = None

        if 'map_inspector_sharable' in options and options['map_inspector_sharable'] == True:
            map_inspector(options['base_segment'], options['base_xy'], options['status_mi'], sharable=True, working_dir=options['working_dir'], rawcsv=option_rawcsv_str)
        else:
            options['map_inspector_sharable'] = False
            map_inspector(options['base_segment'], options['base_xy'], options['status_mi'], working_dir=options['working_dir'], rawcsv=option_rawcsv_str)
    
    x = []
    y = []
    with open(options['base_xy'], "r") as f:
        for line in f:
            coord = line.rstrip().split()
            x.append(float(coord[0]))
            y.append(float(coord[1]))
    return numpy.array(x), numpy.array(y)

def addplot(options):
    __check_rawdata_existence(options)
    __check_rawdata_type(options)

    if options['rawdata_type'] == 'table':
        __check_required_options_for_table(options) # check if required options are given for table type data
        cmd_str = 'mkcsvseg'
        option_str = __make_option_str_for_table(options)
    elif options['rawdata_type'] == 'sound':
        __check_required_options_for_sound(options) # check if required options are given for sound type data
        cmd_str = 'mkfftseg'
        option_str = __make_option_str_for_sound(options)

    __check_basemap_existence(options)
    __set_output_file_for_addplot(options)

    rv = subprocess.run(f"{cmd_str} {option_str} {options['rawdata']} 2> {options['add_segment_log']} > {options['add_segment']}", shell=True)
    if rv.returncode != 0:
        print(f"{cmd_str} command failed. see {options['add_segment_log']}", file=sys.stderr)
        sys.exit(1)

    if 'multi_filter_option' in options:
        multi_filter_add(options)

    rv = subprocess.run(f"toorpia -m add {options['base_segment']} {options['base_xy']} {options['add_segment']} 2> {options['add_xy_log']} > {options['add_xy']}", shell=True)
    if rv.returncode != 0:
        print(f"toorpia command failed. see {options['add_xy_log']}", file=sys.stderr)
        sys.exit(1)
    
    if 'map_inspector' in options and options['map_inspector'] == False:
        None
    else:
        options['map_inspector'] = True
        if 'map_inspector_sharable' in options and options['map_inspector_sharable'] == True:
            map_inspector(options['base_segment'], options['base_xy'], options['add_status_mi'], addplot=options['add_xy'], sharable=True, working_dir=options['working_dir'])
        else:
            options['map_inspector_sharable'] = False
            map_inspector(options['base_segment'], options['base_xy'], options['add_status_mi'], addplot=options['add_xy'], sharable=False, working_dir=options['working_dir'])

    if 'monitoring_scope' in options and options['monitoring_scope'] == True:
        if 'monitoring_scope_sharable' in options and options['monitoring_scope_sharable'] == True:
            monitoring_scope(options['base_xy'], options['add_segment'], options['add_xy'], options['status_ms'], sharable=True)
        else:
            options['monitoring_scope_sharable'] = False
            monitoring_scope(options['base_xy'], options['add_segment'], options['add_xy'], options['status_ms'], sharable=False)
    else:
        options['monitoring_scope'] = False
        options['monitoring_scope_sharable'] = False

    x = []
    y = []
    with open(options['add_xy'], "r") as f:
        for line in f:
            coord = line.rstrip().split()
            x.append(float(coord[0]))
            y.append(float(coord[1]))
    return x, y

def multi_filter(options):
    if not 'multi_filter_option' in options:
        raise Exception("multi_filter_option is required for multi_filter")

    __check_rawdata_type(options)
    if options['rawdata_type'] == 'table':
        raise Exception('filter cannot apply to table type data')
    elif options['rawdata_type'] == 'sound':
        __check_required_options_for_sound(options) # check if required options are given for sound type data

    if not os.path.exists(options['base_segment']):
        raise Exception('base_segment is required')

    if not 'sampling_rate' in options:
        raise Exception('sample_rate is required')

    cmd = '/usr/local/bin/filter'
    option_str = f"-f {options['multi_filter_option']} --sr {options['sampling_rate']}"
    rv = subprocess.run(f"{cmd} {option_str} {options['base_segment']} > {options['working_dir']}/masked_segment.csv", shell=True)
    if rv.returncode != 0:
        print(f"{cmd} command failed.", file=sys.stderr)
        sys.exit(1)
    else:
        os.remove(options['base_segment'])
        os.rename(f"{options['working_dir']}/masked_segment.csv", options['base_segment'])

def multi_filter_add(options):
    if not 'multi_filter_option' in options:
        raise Exception("multi_filter_option is required for multi_filter")

    __check_rawdata_type(options)
    if options['rawdata_type'] == 'table':
        raise Exception('filter cannot apply to table type data')
    elif options['rawdata_type'] == 'sound':
        __check_required_options_for_sound(options) # check if required options are given for sound type data

    if not os.path.exists(options['add_segment']):
        raise Exception('add_segment is required')

    if not 'sampling_rate' in options:
        raise Exception('sample_rate is required')

    cmd = '/usr/local/bin/filter'
    option_str = f"-f {options['multi_filter_option']} --sr {options['sampling_rate']}"
    rv = subprocess.run(f"{cmd} {option_str} {options['add_segment']} > {options['working_dir']}/masked_segment.csv", shell=True)
    if rv.returncode != 0:
        print(f"{cmd} command failed.", file=sys.stderr)
        sys.exit(1)
    else:
        os.remove(options['add_segment'])
        os.rename(f"{options['working_dir']}/masked_segment.csv", options['add_segment'])
