

class MonitoringWarning(Exception):
    pass

class MonitoringError(MonitoringWarning):
    pass

class InfluxDbError(MonitoringError):
    pass
