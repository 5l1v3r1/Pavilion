#!python
"""  Base class to provide a template for all
     subsequent implementations of job launchers to
     follow (i.e. - Moab, slurm, ...)
 """

import sys,os
import subprocess
import time
import datetime
import logging


class BaseJobController():

    """ class to define the common actions for any job type """

    def now(self):
        return datetime.datetime.now().strftime("%m-%d-%YT%H:%M%:%S")

    def __init__(self, name, configs, job_log_file):

        self.name = name
        self.configs = configs
        self.job_log_file = job_log_file

        self.logger = logging.getLogger('pth.runjob.' + self.__class__.__name__)

        self.save_common_settings()

        # move binaries and necessary files to temp working space
        self.setup_working_space()

    def setup_working_space(self):


        ws_path = self.configs['working_space']['path']
        src_dir = self.configs['source_location']
        run_cmd = self.configs['run']['cmd'].split(".", 1)[0]

        if 'NO-WS' in ws_path:
            os.environ['PV_WS'] = src_dir
            os.environ['PV_RUNHOME'] = src_dir
            print os.environ['PV_RUNHOME']
            print 'Working Space: %s' % os.environ['PV_RUNHOME']
            self.logger.info('WS for %s: ' % self.name + os.environ['PV_RUNHOME'])
            return

        # Otherwise ...
        # test specific working space takes first precedence

        if ws_path:
            # it's either a relative path from the src directory
            # or it's an absolute one.
            if '/' in ws_path[0]:
                ws = ws_path
            else:
                ws = src_dir + "/" + ws_path

        # not specified, so place it just under the source location
        # with the default subdir name.
        else:
            ws = src_dir + "/pv_ws"

        # now setup and do the move
        os.environ['PV_WS'] = ws
        os.environ['PV_RUNHOME'] = ws + "/" + self.name + "__" + run_cmd + "." + self.now()

        print 'Working Space: %s' % os.environ['PV_RUNHOME']

        self.logger.info('WS for ' + self.name + ":" + os.environ['PV_RUNHOME'])

        try:
            os.makedirs(os.environ['PV_RUNHOME'], 0o775)
        except:
            print "Error, could not create: ", ws, sys.exc_info()[0]

        to_loc = os.environ['PV_RUNHOME']

        # support user specified files or dirs to copy here.
        files2copy = self.configs['working_space']['files_to_copy']
        if files2copy:
            cmd = "cd " + src_dir + "; rsync -ar " + files2copy + " " + to_loc
        # general case is to copy all except some known source file types
        else:
            from_loc = src_dir + "/"
            cmd = "rsync -a --exclude 'pv_ws' --exclude '*.[ocfh]' --exclude '*.bck' --exclude '*.tar' "
            cmd += from_loc + " " + to_loc


        self.logger.debug('rsync cmd: %s' % cmd)

        try:
            os.system(cmd)
        except:
            print "Error: rsync of src dir to ws failed!"


    def __str__(self):
        return 'instantiated %s object' % self.name

    # return the full path to where the logfile is located
    def get_results_directory(self):
        return os.path.dirname(self.job_log_file)


    # Invoke the correct way of running the job/test as defined in the
    # tests config entry.
    def start(self):
        pass

    # Print all the pertinent run data to the the job log file for later analysis.
    # Most of the <xxxx> stuff is for Gazebo backward compatibility
    def save_common_settings(self):

        obj_name = self.__class__.__name__
        print "#\n#  --- job: ", self.name, "-------"
        print "<rmgr> " + self.configs['run']['scheduler']
        print "<nix_pid> " + str(os.getpid())
        print "<testName> " + self.name
        print "<testExec> " + self.configs['run']['cmd']
        print "<user> " + os.getenv('USER')

        print self.configs

    def build(self):
        pass

    def kill(self):
        pass

    def query(self):
        pass

    def cleanup(self):
        """
            invoke the job specific routine that determines if job failed or passed.
        """
        pass 
        
        
        
# this gets called if it's run as a script/program
if __name__ == '__main__':

    sys.exit()
    
