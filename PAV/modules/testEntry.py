#!python

import sys
import logging
import itertools
from ldms import LDMS
import subprocess
import getpass


def flatten_dict(d):
    def items():
        for key, value in d.items():
            if isinstance(value, dict):
                for subkey, subvalue in flatten_dict(value).items():
                    yield key + "." + subkey, subvalue
            else:
                yield key, value

    return dict(items())


class TestEntry():
    """
    class to manipulate a specific test entry in the test suite
    """

    this_dict = {}
    
    def __init__(self, uid, values, args):

        my_name = self.__class__.__name__
        self.id = uid
        self.name = values['name']
        self.eff_nodes = 1
        self.eff_ppn = None
        self.this_dict[uid] = values
        self.handle = self.id + "-" + self.name
        if args:
            if args['verbose']:
                print "Process test suite entry: " + self.handle
        self.logger = logging.getLogger('pth.' + my_name)
        self.logger.info('Process %s ' % self.handle)

    @staticmethod
    def check_valid(adict):
        # minimal key/values necessary to process this test entry (stanza) any further
        data = flatten_dict(adict)

        # define the required set of elements
        needed = {"source_location", "name", "run.cmd"}
        seen = set(data.keys())

        if needed.issubset(seen):
            for k in needed:
                if not data[k]:
                    print "Error: value must be defined for key: (%s)" % k,
                    return False
            return True
        else:
            missing = ", ".join(needed - seen)
            print "Error: missing the following necessary keys: (%s)" % missing,
            return False

    def get_results_location(self):
        return self.this_dict[self.id]['results']['root']

    def get_type(self):
        #return params['run']['scheduler']
        return self.this_dict[self.id]['run']['scheduler']

    def get_count(self):
        return int(self.this_dict[self.id]['run']['count'])

    def get_values(self):
        return self.this_dict[self.id]

    def get_name(self):
        return self.name

    def get_id(self):
        return self.id

    def set_ppn(self, ppn):
        self.eff_ppn = ppn

    def get_ppn(self):
        return self.eff_ppn

    def set_nnodes(self, nn):
        self.eff_nodes = nn

    def get_nnodes(self):
        return self.eff_nodes

    def get_run_count(self):
        # for now this is as simple as the count, but with a more complex submit
        # strategy (like Gazebo's testMgr) this can be enhanced.
        return self.get_count()

    def room_to_run(self, args):

        # Determined by specific scheduler implementation,
        # otherwise False, there is no room
        return False

    def prep_ldms(self):

        # must be overridden by specific scheduler implementation
        self.logger.info('LDMS not supported for this job (%s) type' % self.handle)
        pass


class MoabTestEntry(TestEntry):

    def get_test_variations(self):
        # figure out all the variations for this test
        # and return list of "new" choices.

        l1 = str(self.this_dict[self.id]['moab']['num_nodes'])
        l2 = str(self.this_dict[self.id]['moab']['procs_per_node'])

        nodes = l1.split(',')
        ppn = l2.split(',')

        tv = []

        for n, p in itertools.product(nodes, ppn):
            # actually create a NEW test entry object that has just the single
            # combination of nodes X ppn
            new_te = TestEntry(self.id, self.this_dict[self.id], None)
            new_te.set_nnodes(n)
            new_te.set_ppn(p)
            tv.append(new_te)

        return tv

    @staticmethod
    def get_active_jobs():
        """
        Find the number of jobs queued or running on the system.
        implement:  `mdiag -j | grep $me | wc -l`
        """
        me = getpass.getuser()

        cat = subprocess.Popen(['mdiag', '-j'],
                               stdout=subprocess.PIPE,
                               )

        grep = subprocess.Popen(['grep', me],
                                stdin=cat.stdout,
                                stdout=subprocess.PIPE,
                                )

        cut = subprocess.Popen(['wc', '-l'],
                               stdin=grep.stdout,
                               stdout=subprocess.PIPE,
                               )

        end_of_pipe = cut.stdout

        for line in end_of_pipe:
            #print 'active_jobs: ', line.strip()
            return int(line.strip())

    def room_to_run(self, args):
        """
        Check system utilization
        so as to not overrun the system.
        """

        active_jobs = MoabTestEntry.get_active_jobs()

        # args w and p should be exclusive, w is first check
        if args['w']:
            if active_jobs < int(args['w'][0]):
                return True
        else:
            if active_jobs < 100:
                return True

        self.logger.info('(%s) Active jobs exceed water mark, no job launched' % self.handle)
        return False

    def prep_ldms(self):

        """ starts LDMS, since it works under Moab """

        self.logger.info('setup LDMS for this job (%s) type' % self.handle)
        LDMS(self)


class RawTestEntry(TestEntry):

    def get_test_variations(self):
        # for now, return list of just myself

        nl = [self]
        return nl

    def room_to_run(self, args):

        # just let er rip for now.  Maybe create a way to throttle number
        # of "jobs" allowed to run...
        return True

    
# this gets called if it's run as a script/program
if __name__ == '__main__':
    sys.exit()
