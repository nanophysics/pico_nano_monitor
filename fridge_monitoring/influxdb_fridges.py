import influxdb
from secrets_file import influx_credentials


class InfluxDB:
    def __init__(
        self,
        addr=influx_credentials["nano_monitor"]["influxdb_url_short"],
        port=443,
        username=influx_credentials["nano_monitor"]["influxdb_user"],
        pw=influx_credentials["nano_monitor"]["influxdb_pass"],
        database=influx_credentials["nano_monitor"]["influxdb_db_name"],
    ):
        print(addr,username,pw, database)
        self.db_client = influxdb.InfluxDBClient(
            host=addr,
            port=port,
            username=username,
            password=pw,
            database=database,
            ssl=True,
            verify_ssl=True,
        )
        print("Databases present in idb instance: ", self.db_client.get_list_database())
    def push_to_influx(self,dict):
            try: 
                self.db_client.write_points(dict)
            except: 
                print('!!! It was not possible to write the data point !!!')

if __name__ == "__main__":
    print("Test")
    InfluxDB()
