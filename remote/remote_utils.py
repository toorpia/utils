import subprocess
import sys
import re
import numpy as np

class toorpia_remote_toolkit:
    def __init__(self, ssh_user, ssh_host, toorpia_service_dir, docker_compose_cmd, analysis_user, working_dir):
        if toorpia_service_dir[0] != '/':
            raise ValueError('toorpia_service_dir must be absolute path')

        if docker_compose_cmd == '' or docker_compose_cmd == None:
            docker_compose_cmd = 'docker compose'

        if working_dir[0] != '/':
            raise ValueError('working_dir must be absolute path')

        regExp = re.compile(r'^[0-9]+$')
        if analysis_user == '' or analysis_user == None:
            raise ValueError('analysis_user must be specified')
        elif not re.match(regExp, analysis_user):
            raise ValueError('analysis_user must be specified as UID')

        self.ssh_info = ssh_user + '@' + ssh_host
        self.working_dir = working_dir

        self.remote_cmd_prefix = f'cd {toorpia_service_dir}; {docker_compose_cmd} exec -T -u {analysis_user} -w {working_dir} toorpia'

        self.toorpia_cmd = "/usr/local/bin/toorpia"

    def exec_remote_cmd(self, cmd, get_output=False):
        if get_output:
            ssh = subprocess.Popen(["ssh", self.ssh_info, cmd],
                            shell=False,
                            text=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
            result = np.array([line.split() for line in ssh.stdout.readlines()], dtype=np.float32)

            if result.size == 0:
                error = ssh.stderr.readlines()
                print >>sys.stderr, "ERROR: %s" % error
            else:
                return result[:,0], result[:,1]
        else:
            subprocess.run(["ssh", self.ssh_info, cmd], shell=False)

    def check_data_type(self, params):
        # regex for automatic checking wav file or csv (table) file. ignore case. 末尾に.gzがついていてもOKとする
        wav_file_regExp = re.compile(r'^.*\.wav(\.gz)?$', re.IGNORECASE)
        csv_file_regExp = re.compile(r'^.*\.csv(\.gz)?$', re.IGNORECASE)
        if params.get('rawdata') is None or params['rawdata'] == '' or params['rawdata'] == None:
            raise ValueError('rawdata must be specified')
        elif not re.match(wav_file_regExp, params['rawdata']) and not re.match(csv_file_regExp, params['rawdata']):
            raise ValueError('rawdata must be wav or csv file')

        if params.get('rawdata_type') is None or params['rawdata_type'] == '' or params['rawdata_type'] == None:
            if re.match(wav_file_regExp, params['rawdata']):
                params['rawdata_type'] = 'sound'
            elif re.match(csv_file_regExp, params['rawdata']):
                if params.get('type_weight_csv') is None or params['type_weight_csv'] == '' or params['type_weight_csv'] == None:
                    params['rawdata_type'] = 'sound'
                else:
                    params['rawdata_type'] = 'table'

        if params['rawdata_type'] != 'sound' and params['rawdata_type'] != 'table':
            raise ValueError('type must be sound or table')

        return params

    def create_basemap(self, params):
        # check params
        params = self.check_data_type(params)

        rawdata = params['rawdata']
        option_str = ''
        make_basesegment_cmd = ''

        if params['rawdata_type'] == 'sound':
            mkseg_cmd = "/usr/local/bin/mkfftseg"
            if params.get('window_length') != None and params['window_length'] != '' and params['window_length'] != None:
                option_str += f' -wl {params["window_length"]}'
            if params.get('sampling_rate') != None and params['sampling_rate'] != '' and params['sampling_rate'] != None:
                option_str += f' -sr {params["sampling_rate"]}'
            make_basesegment_cmd = f'{self.remote_cmd_prefix} {mkseg_cmd} {option_str} {rawdata}  > {self.working_dir}/base_segments.csv 2> {self.working_dir}/base_segments.log'

        elif params['rawdata_type'] == 'table':
            mkseg_cmd = "/usr/local/bin/mkcsvseg"
            if params.get('type_weight_csv') != None and params['type_weight_csv'] != '' and params['type_weight_csv'] != None:
                option_str += f' -o {params["type_weight_csv"]}'
            make_basesegment_cmd = f'{self.remote_cmd_prefix} {mkseg_cmd} {option_str} {rawdata}  > {self.working_dir}/base_segments.csv 2> {self.working_dir}/base_segments.log'

        make_basemap_cmd = f'{self.remote_cmd_prefix} {self.toorpia_cmd} -m base {self.working_dir}/base_segments.csv > {self.working_dir}/base-xy.dat 2> {self.working_dir}/base-xy.log'
        self.exec_remote_cmd(make_basesegment_cmd)
        self.exec_remote_cmd(make_basemap_cmd)

        # get data from remote host
        get_base_xy_cmd = f'{self.remote_cmd_prefix} cat {self.working_dir}/base-xy.dat'
        return self.exec_remote_cmd(get_base_xy_cmd, get_output=True)

    def addplot(self, params):
        # check params
        params = self.check_data_type(params)

        rawdata = params['rawdata']
        option_str = ''
        make_addsegment_cmd = ''

        if params['rawdata_type'] == 'sound':
            mkseg_cmd = "/usr/local/bin/mkfftseg"
            if params.get('window_length') != None and params['window_length'] != '' and params['window_length'] != None:
                option_str += f' -wl {params["window_length"]}'
            if params.get('sampling_rate') != None and params['sampling_rate'] != '' and params['sampling_rate'] != None:
                option_str += f' -sr {params["sampling_rate"]}'
            make_addsegment_cmd = f'{self.remote_cmd_prefix} {mkseg_cmd} {option_str} {rawdata}  > {self.working_dir}/add_segments.csv 2> {self.working_dir}/add_segments.log'
        elif params['rawdata_type'] == 'table':
            mkseg_cmd = "/usr/local/bin/mkcsvseg"
            if params.get('type_weight_csv') != None and params['type_weight_csv'] != '' and params['type_weight_csv'] != None:
                option_str += f' -o {params["type_weight_csv"]}'
            make_addsegment_cmd = f'{self.remote_cmd_prefix} {mkseg_cmd} {option_str} {rawdata}  > {self.working_dir}/add_segments.csv 2> {self.working_dir}/add_segments.log'

        make_addmap_cmd = f'{self.remote_cmd_prefix} {self.toorpia_cmd} -m add {self.working_dir}/base_segments.csv {self.working_dir}/base-xy.dat {self.working_dir}/add_segments.csv > {self.working_dir}/add-xy.dat 2> {self.working_dir}/add-xy.log'
        self.exec_remote_cmd(make_addsegment_cmd)
        self.exec_remote_cmd(make_addmap_cmd)

        # get data from remote host
        get_add_xy_cmd = f'{self.remote_cmd_prefix} cat {self.working_dir}/add-xy.dat'
        return self.exec_remote_cmd(get_add_xy_cmd, get_output=True)
