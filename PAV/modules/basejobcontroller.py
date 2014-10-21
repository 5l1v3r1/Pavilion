#!python
"""  Base class to provide a template for all
     subsequent implementations of job launchers to
     follow (i.e. - Moab, slurm, ...)
 """

import sys
import os
import re
import datetime
import logging
import shutil
import json
from subprocess import Popen, PIPE
import getpass


class JobController():

    """ class to define the common actions for any job type """

    @staticmethod
    def now():
        return datetime.datetime.now().strftime("%m-%d-%YT%H:%M:%S:%f")

    def __init__(self, uid, configs, job_log_file, job_variation):

        self.uid = uid
        self.name = configs['name']
        self.configs = configs
        self.job_log_file = job_log_file
        self.job_variation = job_variation
        self.lh = self.configs['log_handle']

        # setup logging same as in pth
        me = getpass.getuser()
        master_log_dir = '/tmp/' + me
        master_log_file = master_log_dir + '/pth.log'
        self.logger = logging.getLogger('pth.' + self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh = logging.FileHandler(filename=master_log_file)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        #print "initialize job controller"

        # verify command is executable early on
        mycmd = self.configs['source_location'] + "/" + self.configs['run']['cmd']
        is_exec = os.access(mycmd, os.X_OK)
        if not is_exec:
            print mycmd + " command not executable, skipping!"
            self.logger.error('%s %s not executable, skipping!' % (self.lh + ":", mycmd))
            raise RuntimeError('command not executable')

        self.logger.info(self.lh + " : init phase")

        # Define commonly used  global env variables for this job/test.
        # GZ_ vars for backwards compatibility with Gazebo, but to be
        # removed sometime down the road.
        os.environ['PV_TESTNAME'] = self.name
        os.environ['GZ_TESTNAME'] = self.name
        os.environ['PV_TESTEXEC'] = self.configs['run']['cmd']
        os.environ['GZ_TESTEXEC'] = self.configs['run']['cmd']
        os.environ['GZ_TEST_PARAMS'] = self.configs['run']['test_args']
        os.environ['PV_TEST_ARGS'] = self.configs['run']['test_args']

    def setup_working_space(self):

        ws_path = self.configs['working_space']['path']
        src_dir = self.configs['source_location']
        run_cmd = self.configs['run']['cmd'].split(".")[0]

        exclude_ws = ''
        if ws_path:
            # it's either a relative path to the src directory
            # or it's an absolute one.
            if '/' in ws_path[0]:
                ws = ws_path
            else:
                ws = src_dir + "/" + ws_path
                exclude_ws = ws_path

        # working space is null, so run from source directory
        # and no further work necessary.
        else:
            os.environ['PV_WS'] = ""
            os.environ['PV_RUNHOME'] = src_dir
            print os.environ['PV_RUNHOME']
            print 'Working Space: %s' % os.environ['PV_RUNHOME']
            self.logger.info('WS for %s: ' % self.lh + os.environ['PV_RUNHOME'])
            return

        # now setup and do the move
        os.environ['PV_RUNHOME'] = ws + "/" + self.name + "__" + run_cmd + "." + JobController.now()

        print 'Working Space: %s' % os.environ['PV_RUNHOME']

        self.logger.info(self.lh + " : " + 'Create WS - ' + os.environ['PV_RUNHOME'])

        try:
            os.makedirs(os.environ['PV_RUNHOME'], 0o775)
        except OSError:
            print "Error, could not create: ", ws, sys.exc_info()[0]
            self.logger.error(self.lh + " Can't create temporary work space, skipping test!")
            return

        to_loc = os.environ['PV_RUNHOME']
        os.environ['PV_WS'] = to_loc

        # support user specified files or dirs to copy here.
        files2copy = self.configs['working_space']['copy_to_ws']
        if files2copy:
            cmd = "cd " + src_dir + "; rsync -ar " + files2copy + " " + to_loc
        # general case is to copy all files except some known source file types
        else:
            from_loc = src_dir + "/"
            if exclude_ws:
                cmd = "rsync -a --exclude '" + \
                      exclude_ws + "' --exclude '*.[ocfh]' --exclude '*.bck' --exclude '*.tar' "
            else:
                cmd = "rsync -a --exclude '*.[ocfh]' --exclude '*.bck' --exclude '*.tar' "
            cmd += from_loc + " " + to_loc

        self.logger.debug('%s : %s' % (self.lh, cmd))

        # run the command
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, errors = p.communicate()

        if p.returncode or errors:
            print "Error: failed copying data to working space!"
            print [p.returncode, errors, output]
            self.logger.info(self.lh + " failed copying data to working space!, skipping job: " + self.name +
                                       "(Hint: check the job logfile)")

    def __str__(self):
        return 'instantiated %s object' % self.name

    # return the full path to where the logfile is located
    def get_results_directory(self):
        return os.path.dirname(self.job_log_file)

    # Print all the pertinent run data to the the job log file for later analysis.
    # Most of the <xxxx> stuff is for Gazebo backward compatibility
    def save_common_settings(self):

        print "#\n#  --- job: ", self.name, "-------"
        print "<rmgr> " + self.configs['run']['scheduler']
        print "<nix_pid> " + str(os.getpid())
        print "<testName> " + self.name
        print "<testExec> " + self.configs['run']['cmd']
        print "<user> " + os.getenv('USER')
        print "<params> " + os.environ['PV_TEST_ARGS']
        print "<segName> " + "theTargetSeg"
        sys.stdout.flush()

        # save the test config
        tcf = os.environ["PV_JOB_RESULTS_LOG_DIR"] + "/test_config.txt"
        tcf_file = open(tcf, "w+")
        tcf_file.write("Pavilion configuration values used to run this test:\n\n")
        tcf_file.write(json.dumps(self.configs, sort_keys=True, indent=4))
        tcf_file.close()

    def build(self):
        # call the command that builds the users test/job
        bld_cmd = self.configs['source_location'] + "/" + self.configs['build']['cmd']
        self.logger.info(self.lh + ': start build command: ' + bld_cmd)
        os.system(bld_cmd)
        self.logger.info(self.lh + '%s build command complete ' % bld_cmd)

    def query(self):
        pass

    def run_epilog(self):
        es = self.configs['results']['epilog_script']

        # run an epilog script if defined in the test config
        if es:
            self.logger.info(self.lh + ': start epilog script: ' + es)
            os.system(es)
            self.logger.info(self.lh + '%s epilog script complete' % es)

    def setup_job_info(self):

        # save for later reference
        os.environ['PV_SAVE_FROM_WS'] = self.configs['working_space']['save_from_ws']

        os.environ['PV_ES'] = self.configs['results']['epilog_script']

        os.environ['GZ_RUNHOME'] = os.environ['PV_RUNHOME']

        os.environ['GZ_LOGFILE'] = os.environ["PV_JOB_RESULTS_LOG"]

        os.environ['PV_TEST_ARGS'] = self.configs['run']['test_args']
        os.environ['GZ_TEST_PARAMS'] = os.environ['PV_TEST_ARGS']

    def cleanup(self):

        self.logger.info(self.lh + ': start cleanup')

        sys.stdout.flush()
        sys.stderr.flush()

        # Save the necessary files from the RUNHOME directory
        from_loc = os.environ['PV_RUNHOME'] + "/"
        to_loc = os.environ["PV_JOB_RESULTS_LOG_DIR"]

        files2copy = ''
        #if (self.configs['working_space']['save_from_ws']):
        if os.environ['PV_SAVE_FROM_WS']:
            files2copy = " --include " + os.environ['PV_SAVE_FROM_WS']

        # add the basics
        files2copy += " --include '*.log' --include '*.std*' --exclude='*' "

        # finalize complete command
        cmd = "rsync -ar " + files2copy + " " + from_loc + " " + to_loc

        self.logger.debug('%s : %s' % (self.lh, cmd))

        # do it
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, errors = p.communicate()

        if p.returncode or errors:
            print "Error: failure copying job results the output directory!"
            print [p.returncode, errors, output]
            self.logger.info(self.lh + " failure copying job results to the output directory: " + self.name +
                                       "(Hint: check the job's logfile)")

        # remove the working space if it was created
        #if self.configs['working_space']['path']:
        if os.environ['PV_WS']:
            self.logger.info('%s : remove WS - %s ' % (self.lh, os.environ['PV_RUNHOME']))
            shutil.rmtree(os.environ['PV_RUNHOME'])

    @staticmethod
    def process_trend_data():

        # slurp up the trend data from the log file and place it in a file
        # called trend_data in the results dir
        tdf = os.environ["PV_JOB_RESULTS_LOG_DIR"] + "/trend_data"
        out_file = open(tdf, "w")

        lf = open(os.environ["PV_JOB_RESULTS_LOG"], 'r')

        for line in lf:
            match = re.search("^(<td>\s+(.*))", line, re.IGNORECASE)
            if match:
                out_file.write(match.group(2) + "\n")

        out_file.close()


# this gets called if it's run as a script/program
if __name__ == '__main__':

    sys.exit()