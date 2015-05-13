#!python


#  ###################################################################
#
#  Disclaimer and Notice of Copyright 
#  ==================================
#
#  Copyright (c) 2015, Los Alamos National Security, LLC
#  All rights reserved.
#
#  Copyright 2015. Los Alamos National Security, LLC. 
#  This software was produced under U.S. Government contract 
#  DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL), 
#  which is operated by Los Alamos National Security, LLC for 
#  the U.S. Department of Energy. The U.S. Government has rights 
#  to use, reproduce, and distribute this software.  NEITHER 
#  THE GOVERNMENT NOR LOS ALAMOS NATIONAL SECURITY, LLC MAKES 
#  ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY 
#  FOR THE USE OF THIS SOFTWARE.  If software is modified to 
#  produce derivative works, such modified software should be 
#  clearly marked, so as not to confuse it with the version 
#  available from LANL.
#
#  Additionally, redistribution and use in source and binary 
#  forms, with or without modification, are permitted provided 
#  that the following conditions are met:
#  -  Redistributions of source code must retain the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer. 
#  -  Redistributions in binary form must reproduce the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer in the documentation 
#     and/or other materials provided with the distribution. 
#  -  Neither the name of Los Alamos National Security, LLC, 
#     Los Alamos National Laboratory, LANL, the U.S. Government, 
#     nor the names of its contributors may be used to endorse 
#     or promote products derived from this software without 
#     specific prior written permission.
#   
#  THIS SOFTWARE IS PROVIDED BY LOS ALAMOS NATIONAL SECURITY, LLC 
#  AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
#  IN NO EVENT SHALL LOS ALAMOS NATIONAL SECURITY, LLC OR CONTRIBUTORS 
#  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, 
#  OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
#  OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
#  OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
#  OF SUCH DAMAGE.
#
#  ###################################################################


"""  Implementation of Moab Job Controller  """

import sys
import os
import subprocess
import re
from basejobcontroller import JobController
from helperutilities import which


class MoabJobController(JobController):
    """ class to run a job using Moab """

    @staticmethod
    def is_moab_system():
        #if os.path.isfile("/etc/toss-release"):
        if which("mdiag"):
            return True
        else:
            return False

    # .. some setup and let the msub command fly ...
    def start(self):

        # Stuff any buffered output into the output file now
        # so that the the order doesn't look all mucked up
        sys.stdout.flush()

        msub_cmd = "msub -V "

        # handle optionally specified queue
        if self.configs['moab']['queue']:
            msub_cmd += self.configs['moab']['queue'] + " "

        # add test name
        msub_cmd += "-N " + self.name + " "

        # get time limit, if specified
        time_lim = ''
        try:
            time_lim = str(self.configs['moab']['time_limit'])
            self.logger.info(self.lh + " : time limit = " + time_lim)
        except TypeError:
            self.logger.info(self.lh + " Error: time limit value, test suite entry may need quotes")

        # get target segment, if specified
        ts = ''
        if self.configs['moab']['target_seg']:
            ts = self.configs['moab']['target_seg']

        reservation = ''
        if self.configs['moab']['reservation']:
            reservation = self.configs['moab']['reservation']

        node_list = ''
        if self.configs['moab']['node_list']:
            node_list = self.configs['moab']['node_list']

        # accounting file? or just log it?

        # variation passed as arg0 - nodes, arg1 - ppn
        nnodes = str(self.configs['moab']['num_nodes'])
        #nnodes = str(self.job_variation[0])
        #ppn = str(self.job_variation[1])
        ppn = str(self.configs['moab']['procs_per_node'])

        self.logger.info(self.lh + " : nnodes=" + nnodes)
        self.logger.info(self.lh + " : ppn=" + ppn)
        self.logger.info(self.lh + " : args=" + str(self.configs['run']['test_args']))

        pes = int(ppn) * int(nnodes)
        self.logger.info(self.lh + " : npes=" + str(pes))

        os.environ['GZ_PESPERNODE'] = ppn
        os.environ['PV_PESPERNODE'] = ppn

        os.environ['GZ_NNODES'] = nnodes
        os.environ['PV_NNODES'] = nnodes
        print "<nnodes> " + nnodes

        os.environ['PV_NPES'] = str(pes)
        os.environ['GZ_NPES'] = os.environ['PV_NPES']
        print "<npes> " + str(pes)

        # create working space here so that each msub run gets its own
        #self.setup_working_space()

        # print the common log settings here right after the job is started
        self.save_common_settings()

        # store some info into ENV variables that jobs may need to use later on.
        self.setup_job_info()

        # setup unique Moab stdout and stderr file names
        # Handle differences between moab-slurm, moab-cle, etc. ??
        se = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stderr"
        so = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stdout"
        msub_cmd += "-o " + so + " -e " + se + " "

        if node_list:
            msub_cmd += "-l nodes=" + node_list
        else:
            msub_cmd += "-l nodes=" + nnodes
        if time_lim:
            msub_cmd += ",walltime=" + time_lim
        if ts:
            msub_cmd += ",feature=" + ts
        if reservation:
            msub_cmd += ",advres=" + reservation

        run_cmd = os.environ['PV_RUNHOME'] + "/" + self.configs['run']['cmd']
        os.environ['USER_CMD'] = run_cmd

        msub_cmd += " " + os.environ['PVINSTALL'] + "/PAV/modules/moab_job_handler.py"

        if MoabJobController.is_moab_system():
            self.logger.info(self.lh + " : " + msub_cmd)
            # call to invoke real Moab command
            output = subprocess.check_output(msub_cmd, shell=True)
            # Finds the jobid in the output from msub. The job id can either
            # be just a number or Moab.number.
            match = re.search("^((Moab.)?(\d+))[\r]?$",  output, re.IGNORECASE | re.MULTILINE)
            jid = 0
            if match.group(1):
                jid = match.group(1)
            print "<JobID> " + str(jid)

        else:
            # fake-out section to run on basic unix system
            fake_job_cmd = os.environ['PVINSTALL'] + "/PAV/modules/moab_job_handler.py"
            p = subprocess.Popen(fake_job_cmd, stdout=self.job_log_file, stderr=self.job_log_file, shell=True)
            # wait for the subprocess to finish
            (output, errors) = p.communicate()
            if p.returncode or errors:
                print "Error: something went wrong!"
                print [p.returncode, errors, output]
                self.logger.info(self.lh + " run error: " + errors)

    
# this gets called if it's run as a script/program
if __name__ == '__main__':
    sys.exit()
