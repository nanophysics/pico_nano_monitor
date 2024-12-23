import logging
import os
import influxdb
from secrets_file import influx_credentials
from constants import InfluxDbError

logger = logging.getLogger(__file__)


class InfluxDB:
    def __init__(
        self,
        addr=influx_credentials["nano_monitor"]["influxdb_url_short"],
        port=443,
        username=influx_credentials["nano_monitor"]["influxdb_user"],
        pw=influx_credentials["nano_monitor"]["influxdb_pass"],
        database=influx_credentials["nano_monitor"]["influxdb_db_name"],
    ):
        logger.info(f"InfluxDB {addr=} {username=} {database=}")
        if os.environ.get("MOCK_INFLUXDB", None):
            logger.info("MOCK_INFLUXDB")
            return

        try:
            self.db_client = influxdb.InfluxDBClient(
                host=addr,
                port=port,
                username=username,
                password=pw,
                database=database,
                ssl=True,
                verify_ssl=True,
            )
        except Exception as e:
            logger.exception(e)
            raise InfluxDbError(f"Failed to connect to influx: {e!r}") from e

        logger.info(
            f"Databases present in idb instance: {self.db_client.get_list_database()}"
        )

    def close(self) -> None:
        self.db_client.close()

    def push_to_influx(self, measurements: list[dict]) -> None:
        if os.environ.get("MOCK_INFLUXDB", None):
            logger.debug(f"MOCK_INFLUXDB: {measurements}")
            return

        try:
            logger.debug(f"push_to_influx({len(measurements)} measurements)")
            self.db_client.write_points(measurements)
        except Exception as e:
            raise InfluxDbError(
                f"Could not write data point: {e!r}"
            ) from e
