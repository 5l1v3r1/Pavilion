#!python

import datetime
import grp
import os
import stat
from pavilion.module_actions import ModuleAction
import pavilion.module_wrapper

""" Class to allow for scripts to be written for other modules.
    Typically, this will be used to write bash or batch scripts. 
"""

def get_action(mod_line):
    """Function to return the type of action requested by the user for a
       given module, using the pavilion configuration syntax.  The string can
       be in one of three formats:
       1) '[mod-name]' - The module 'mod-name' is to be loaded.
       2) '[old-mod-name]->[mod-name]' - The module 'old-mod-name' is to be
                                         swapped out for the module 'mod-name'.
       3) '-[mod-name]' - The module 'mod-name' is to be unlaoded.
       :param str mod_line: String provided by the user in the config.
       :return object action: Return the appropriate object as provided by
                              the module_actions file.
    """
    if '->' in mod_line:
        return 'swap'
    elif mod_line.startswith('-'):
        return 'unload'
    else:
        return 'load'

def get_name(mod_line):
    """Function to return the name of the module based on the config string
       provided by the user.  The string can be in one of three formats:
       1) '[mod-name]' - The module 'mod-name' is the name returned.
       2) '[old-mod-name]->[mod-name]' - The module 'mod-name' is returned.
       3) '-[mod-name]' - The module 'mod-name' is the name returned.
       :param str mod_line: String provided by the user in the config.
       :return str modn_name: The name of the module to be returned.
    """
    if '->' in mod_line:
        return mod_line[mod_line.find('->')+2,]
    elif mod_line.startswith('-'):
        return mod_line[1:]
    else:
        return mod_line

def get_old_swap(mod_line):
    """Function to return the old module name in the case of a swap.
       :param str mod_line: String provided by the user in the config.
       :return str mod_old: Name of module to be swapped out.
    """
    return mod_line[:mod_line.find('->')-1]


class ScriptComposerError(RuntimeError):
    """Class level exception during script composition."""


class ScriptHeader(object):
    """Class to serve as a struct for the script header."""

    def __init__(self, shell_path=None, scheduler_headers=None):
        """Function to set the header values for the script.
        :param string shell_path: Shell path specification.  Typically
                                  '/bin/bash'.  default = None.
        :param list scheduler_headers: List of lines for scheduler resource
                                       specifications.
        """
        self.shell_path = shell_path
        self.scheduler_headers = scheduler_headers

    @property
    def shell_path(self):
        """Function to return the value of the internal shell path variable."""
        return self._shell_path

    @shell_path.setter
    def shell_path(self, value):
        """Function to set the value of the internal shell path variable."""
        if value is None:
            value = '#!/bin/bash'

        self._shell_path = value

    @property
    def scheduler_headers(self):
        """Function to return the list of scheduler header lines."""
        return self._scheduler_headers

    @scheduler_headers.setter
    def scheduler_headers(self, value):
        """Function to set the list of scheduler header lines."""
        if value is None:
            value = []

        self._scheduler_headers = value

    def get_lines(self):
        """Function to retrieve a list of lines for the script header."""
        ret_list = [self.shell_path]

        for part in self.scheduler_headers:
            ret_list.append(part)

        return ret_list

    def reset(self):
        """Function to reset the values of the internal variables back to
        None.
        """
        self.__init__()


class ScriptDetails(object):
    """Class to contain the final details of the script."""

    def __init__(self, name=None, group=None, perms=None):
        """Function to set the final details of the script.
        :param string name: Specify a name for the script. 
                                   default = 'pav_(date)_(time)'
        :param string group: Name of group to set as owner of the file. 
                             default = user default group
        :param int perms: Value for permission on the file (see
                          `man chmod`).  default = 0o770
        """
        self.name = name
        self.group = group
        self.perms = perms

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value is None:
            value = "_".join(datetime.datetime.now().__str__().split())

        self._name = value

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, value):
        if value is None:
            value = str(os.environ['USER'])

        self._group = value

    @property
    def perms(self):
        return self._perms

    @perms.setter
    def perms(self, value):
        if value is None:
            value = 0o770

        self._perms = value

    def reset(self):
        self.__init__()


class ScriptComposer(object):

    def __init__(self, header=None, details=None):
        """Function to initialize the class and the default values for all of
        the variables.
        """

        self.header = header

        self.details = details

        self._script_lines = []

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, header):
        if header is None:
            self._header = ScriptHeader()

        self._header = header_obj

    @property
    def details(self):
        return self._details

    @details.setter
    def details(self, details):
        if details is None:
            self._details = ScriptDetails()

        self._details = details

    def reset(self):
        """Function to reset all variables to the default."""
        self.__init__()

    def envChange(self, var, value):
        """Function to take the environment variable change requested by the
        user and add the appropriate line to the script.
        :param str var: The variable name.
        :param str value: The variable value. None unsets variable.
        """

        if value is not None:
            self._script_lines.append('export {}={}'.format(var, value))
        else:
            self._script_lines.append('unset {}'.format(var))

    def moduleChange(self, mod_name):
        """Function to take the module changes specified in the user config
        and add the appropriate lines to the script.
        :param Union(list, str) mod_name: Name of a module or a list thereof in
                                          the format used in the user config.
        """

        mod_obj_list = []

        for mod in mod_name:
            self.addNewline()
            fullname = get_name(mod)
            if '/' in fullname:
                name, version = fullname.split('/')
            else:
                name = fullname
                version = None
            action = get_action(mod)

            module_obj = module_wrapper.get_module_wrapper(name, version)

            if action == 'load':
                mod_act, mod_env = module_obj.load()

                for act in mod_act:
                    if isinstance(act, str):
                        self._script_lines.append(act)
                    elif issubclass(act, ModuleAction):
                        self._script_lines.extend([act.action(), act.verify()])

                self.envChange(mod_env)

            elif action == 'unload':
                mod_act, mod_env = module_obj.unload()

                for act in mod_act:
                    if isinstance(act, str):
                        self._script_lines.append(act)
                    elif issubclass(act, ModuleAction):
                        self._script_lines.extend([act.action(), act.verify()])

                self.envChange(mod_env)

            elif action == 'swap':
                old = get_old_swap(mod)
                if '/' in old:
                    oldname, oldver = old.split('/')
                else:
                    oldname = old
                    oldver = None

                mod_act, mod_env = module_obj.swap(old_module_name=oldname,
                                                            old_version=oldver)

                for act in mod_act:
                    if isinstance(act, str):
                        self._script_lines.append(act)
                    elif issubclass(act, ModuleAction):
                        self._script_lines.extend([act.action(), act.verify()])

                self.envChange(mod_env)

    def addNewline(self):
        """Function that just adds a newline to the script lines."""
        self._script_lines.append('\n')

    def addComment(self, comment):
        """Function for adding a comment to the script.
        :param str comment: Text to be put in comment without the leading '# '.
        """
        self._script_lines.append("# {}".format(comment))

    def addCommand(self, command):
        """Function to add a line unadulterated to the script lines.
        :param str command: String representing the whole command to add.
        """
        if isinstance(command, list):
            for cmd  in command:
                self._script_lines.append(cmd)
        elif isinstance(command, str):
            self._script_lines.append(command)

    def writeScript(self, dirname=os.getcwd()):
        """Function to write the script out to file.
        :param string dirname: Directory to write the file to.  default=$(pwd)
        :return bool result: Returns either True for successfully writing the
                             file or False otherwise.
        """

        file_name = self.details.name

        if not os.path.isabs(file_name):
            file_name = os.path.join(dirname, file_name)

        with open(file_name, 'w') as script_file:

            script_file.writelines(self._script_lines)
    
            scriptfno = script_file.fileno()
    
            os.chmod(scriptfno, self.details.perms)
    
            try:
                grp_st = grp.getgrnam(self.details.group)
            except KeyError:
                error = "Group {} not found on this machine.".format(
                                                            self.details.group)
                raise ScriptComposerError(error)
    
            gid = grp_st.gr_gid
    
            os.chown(scriptfno, uid, gid)

        return True
