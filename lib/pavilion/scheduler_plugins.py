import collections
from pavilion.variables import VariableSetManager
from yapsy import IPlugin
import logging
import re

LOGGER = logging.getLogger('pav.{}'.format(__name__))

class SchedulerPluginError(RuntimeError):
    pass

_SCHEDULER_PLUGINS = None
_LOADED_PLUGINS = None

_SCHEDULER_VARS = [ 'num_nodes', 'procs_per_node', 'qos', 'reservation',
                    'partition', 'account', 'down_nodes', 'unused_nodes',
                    'busy_nodes', 'maint_nodes', 'other_nodes', 'chunk_size' ]

class SchedVarDict( collections.UserDict ):

    def __init__( self ):
        global _SCHEDULER_PLUGINS
        if _SCHEDULER_PLUGINS is not None:
            raise SchedulerPluginError(
                  "Dictionary of scheduler plugins can't be generated twice." )
        super().__init__( {} )
        _SCHEDULER_PLUGINS = self

    def __getitem__( self, name, var ):
        if name not in self.data:
            self.data[ name ][ var ] = \
                             get_scheduler_plugin( name ).get( var )
        return self.data[ name ]

    def _reset( self ):
        LOGGER.warning( "Resetting the plugins.  This functionality exists " +\
                        "only for use by unittests." )
        _reset_plugins()
        self.data = {}

def _reset_plugins():
    global _SCHEDULER_PLUGINS

    if _SCHEDULER_PLUGINS is not None:
        for key in list(_SCHEDULER_PLUGINS.keys()):
            remove_system_plugins( key )

def add_scheduler_plugin( scheduler_plugin ):
    global _SCHEDULER_PLUGINS
    name = scheduler_plugin.name

    if _LOADED_PLUGINS is None:
        _LOADED_PLUGINS = {}

    if name not in _LOADED_PLUGINS:
        _LOADED_PLUGINS[ name ] = scheduler_plugin
    elif scheduler_plugin.priority > _LOADED_PLUGINS[name].priority:
        _LOADED_PLUGINS[ name ] = scheduler_plugin
        LOGGER.warning( "Scheduler plugin {} replaced due to priority".format(
                        name ) )
    elif priority < _LOADED_PLUGINS[name].priority:
        LOGGER.warning( "Scheduler plugin {} ignored due to priority".format(
                        name ) )
    elif priority == _LOADED_PLUGINS[name].priority:
        raise SchedulerPluginError("Two plugins for the same system plugin "
                                "have the same priority {}, {}."
                                .format(scheduler_plugin,
                                        _LOADED_PLUGINS[name]))

def remove_scheduler_plugin( scheduler_plugin ):
    global _SCHEDULER_PLUGINS
    name = scheduler_plugin.name

    if name in _SCHEDULER_PLUGINS:
        del _SCHEDULER_PLUGINS[ name ]

def get_scheduler_plugin( name ):
    global _LOADED_PLUGINS

    if _LOADED_PLUGINS is None:
        raise SchedulerPluginError(
                              "Trying to get plugins before they are loaded." )

    if name not in _LOADED_PLUGINS:
        raise SchedulerPluginError("Module not found: '{}'".format(name))

    return _LOADED_PLUGINS[ name ]

class SchedulerPlugin(IPlugin.IPlugin):

    PRIO_DEFAULT = 0
    PRIO_COMMON = 10
    PRIO_USER = 20

    NAME_VERS_RE = re.compile(r'^[a-zA-Z0-9_.-]+$')

    def __init__( self, name, priority=PRIO_DEFAULT ):
        """Scheduler plugin that is expected to be overriden by subclasses.
        The plugin will populate a set of expected 'sched' variables."""

        super().__init__()

        self.logger = logging.getLogger( 'sched.' + name )
        self.name = name
        self.priority = priority
        self.values = {}
        for var in _SCHEDULER_VARS:
            self.values[ var ] = None

    def _get( var ):
        raise NotImplemented

    def get( var ):
        global _SCHEDULER_VARS

        if var not in _SCHEDULER_VARS:
            raise SchedulerPluginError( "Requested variable {}".format( var )+\
                              " not in the expected list of variables." )

        if self.values[ var ] is None:
            val = self._get( var )

            ge_set = [ 'num_nodes', 'down_nodes', 'unused_nodes', 'busy_nodes',
                       'maint_nodes', 'other_nodes', 'chunk_size' ]
            if var in ge_set and val < 0:
                raise SchedulerPluginError( "Value for '{}' ".format( var ) +\
                                            "must be greater than or equal " +\
                                            "to zero.  Received '{}'.".format(
                                            val ) )
            if var == 'procs_per_node' and val <= 0:
                raise SchedulerPluginError( "Value for 'procs_per_node' " +\
                                            "must be greater than zero.  " +\
                                            "Received '{}'.".format( val ) )

            self.values[ var ] = val

        return self.values[ var ]

    def set( var, val ):
        global _SCHEDULER_VARS

        if var not in _SCHEDULER_VARS:
            raise SchedulerPluginError( "Specified variable {}".format( var )+\
                                    " not in the expected list of variables." )

        if var in [ 'down_nodes', 'unused_nodes', 'busy_nodes', 'maint_nodes',
                    'other_nodes' ]:
            raise SchedulerPluginError( "Attempting to set a variable that" + \
                                        " is not meant to be set by the " + \
                                        "user.  Variable: {}.".format( var ) )

        if self.values[ var ] is not None:
            logger.warning( "Replacing value for {} from ".format( var ) + \
                            "{} to {}.".format( self.values[ var ], val ) )

        self.values[ var ] = val

    def activate(self):
        """Add this plugin to the system plugin list."""

        add_scheduler_plugin( self )

    def deactivate(self):
        """Remove this plugin from the system plugin list."""

        remove_scheduler_plugin( self )

    def __reset():
        """Remove this plugin and its changes."""

        self.values = None
        self.deactivate()
