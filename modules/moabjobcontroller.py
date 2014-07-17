#!python
"""  Implementation of Moab Job Controller  """

import sys, os
import subprocess
from basejobcontroller import BaseJobController
import time
import itertools


def find_jobid(message):
    '''Finds the jobid in the output from nsub. The job id can either
    be just a number or Moab.number.'''
    # Optional \r because Windows python2.4 can't figure out \r\n is newline
    match=re.search("^((Moab.)?(\d+))[\r]?$",message,re.IGNORECASE|re.MULTILINE)
    if match:
        return match.group(1)
    return None

def find_moab_node_list():
    return "mu123 mu456"



class MoabJobController(BaseJobController):
    """ class to run a job using Moab """


    # .. some setup and let the msub command fly ...
    def start(self):

        # Get any buffered output into the output file now
        # so that the the order doesn't look all mucked up
        sys.stdout.flush()

        msub_cmd = "msub -V "

        # handle optionally specified queue
        if self.configs['moab']['queue']:
            msub_cmd += self.configs['moab']['queue'] + " "

        # add test name
        msub_cmd += "-N " + self.name + " "

        # get time limit, if specified
        time_lim = self.configs['moab']['time_limit']

        # get target segment, if specified
        ts = ''
        if self.configs['moab']['target_seg']:
            ts = self.configs['moab']['target_seg']

        # accounting file? or just log it?

        # variation passed as arg0 - nodes, arg1, ppn
        nnodes = str(self.job_variation[0])
        ppn = str(self.job_variation[1])

        self.logger.info(self.lh + " : nnodes=" + nnodes)

        pes = int(ppn) * int(nnodes)

        self.logger.info(self.lh + " : npes=" + str(pes))
        os.environ['GZ_PESPERNODE'] = ppn
        os.environ['PV_PESPERNODE'] = ppn

        os.environ['GZ_NNODES'] = nnodes
        os.environ['PV_NNODES'] = nnodes
        print "<nnodes> " + nnodes

        os.environ['PV_NPES'] = str(pes)
        print "<npes> " + str(pes)

        # create working space here so that each msub run gets its own
        self.setup_working_space()

        # print the common log settings here right after the job is started
        self.save_common_settings()

        # setup unique Moab stdout and stderr file names
        # Handle differences between moab-slurm, moab-cle, etc. ??
        so = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stderr"
        se = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stdout"
        msub_cmd += "-o " + so + " -e " + se + " "

        msub_cmd += "-l nodes=" + nnodes + ",walltime=" + time_lim
        if ts:
            msub_cmd += ",feature=" + ts

        run_cmd =  os.environ['PV_RUNHOME'] + "/" + self.configs['run']['cmd']
        os.environ['USER_CMD'] = run_cmd

        # invoke msub and print jobid
        msub_cmd += " " + "./moab_job_handler"
        self.logger.info(self.lh + " : " + msub_cmd)

        # change to msub_cmd when on msub system
        p = subprocess.Popen(run_cmd, stdout=self.job_log_file, stderr=self.job_log_file, shell=True)
        # wait for the subprocess to finish
        (output,errors) = p.communicate()

        if p.returncode or errors:
            print "Error: something went wrong!"
            self.logger.info(self.lh + " run error: " + errors)
            print [p.returncode, errors, output]

        # dummy line until on real Moab system
        jobid = 3
        #jobid = find_jobid(output)
        print "<JobID> " + str(jobid)
        self.logger.info(self.lh + " job %s launched!" % str(jobid))

        print "<nodes> " + find_moab_node_list()

    
# this gets called if it's run as a script/program
if __name__ == '__main__':
    
    # instantiate a class to handle the config files
    mjc = MoabJobController()

    sys.exit()
    
