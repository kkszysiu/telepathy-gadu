import telepathy
import gobject
import dbus
import logging

from gadu.connection import GaduConnection

__all__ = ['GaduConnectionManager']

logger = logging.getLogger('Gadu.ConnectionManager')


class GaduConnectionManager(telepathy.server.ConnectionManager):
    """Gadu connection manager
    
    Implements the org.freedesktop.Telepathy.ConnectionManager interface"""

    def __init__(self, shutdown_func=None):
        "Initializer"
        telepathy.server.ConnectionManager.__init__(self, 'gadu')

        self._protos['gadugadu'] = GaduConnection
        self._shutdown = shutdown_func
        logger.info("Connection manager created")

    def GetParameters(self, proto):
        "Returns the mandatory and optional parameters for the given proto."
        if proto not in self._protos:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

        result = []
        connection_class = self._protos[proto]
        mandatory_parameters = connection_class._mandatory_parameters
        optional_parameters = connection_class._optional_parameters
        default_parameters = connection_class._parameter_defaults

        for parameter_name, parameter_type in mandatory_parameters.iteritems():
            param = (parameter_name,
                    telepathy.CONN_MGR_PARAM_FLAG_REQUIRED,
                    parameter_type,
                    '')
            result.append(param)

        for parameter_name, parameter_type in optional_parameters.iteritems():
            if parameter_name in default_parameters:
                param = (parameter_name,
                        telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT,
                        parameter_name,
                        default_parameters[parameter_name])
            else:
                param = (parameter_name, 0, parameter_name, '')
            result.append(param)

        return result

    def disconnected(self, conn):
        def shutdown():
            if self._shutdown is not None and \
                    len(self._connections) == 0:
                self._shutdown()
            return False
        result = telepathy.server.ConnectionManager.disconnected(self, conn)
        gobject.timeout_add(5000, shutdown)

    def quit(self):
        "Terminates all connections. Must be called upon quit"
        for connection in self._connections:
            connection.Disconnect()
        logger.info("Connection manager quitting")
