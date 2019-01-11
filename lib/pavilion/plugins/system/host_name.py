import subprocess
import pavilion.varaibles
import pavilion.system_plugins as system_plugins

class HostName( system_plugins.SystemPlugins ):

    def __init__( self, sub_keys=[ None ] ):
        super.__init__( 'host_name', 10, True, sub_keys )

    def _get( self ):
        """Base method for determining the host name."""

        if sub_key not in self.sub_keys:
            raise KeyError("Sub-key '{}' not found on sys variable {}.".format(
                           sub_key, self.name))

        self.values[ None ] = subprocess.check_output(['hostname', '-s'])
        self.values[ None ] = self.values[ None ].strip().decode('UTF-8')

        return self.values
