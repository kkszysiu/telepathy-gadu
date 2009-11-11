import telepathy

class GaduDebug(telepathy.server.Debug):
    """Gadu debug interface

    Implements the org.freedesktop.Telepathy.Debug interface"""

    def __init__(self, conn_manager):
        telepathy.server.Debug.__init__(self, conn_manager)

    def get_record_name(self, record):
        name = record.name
        if name.startswith("Gadu."):
            domain, category = name.split('.', 1)
        else:
            domain = "gadu"
            category = name
        name = domain.lower() + "/" + category.lower()
        return name
