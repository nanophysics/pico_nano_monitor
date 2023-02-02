from dataclasses import dataclass
import os
import re
import numpy as np
from influxdb_fridges import InfluxDB


@dataclass(frozen=True)
class Fridge:
    logging_device: str
    setup: str
    room: str
    user: str
    log_folder: str
    manufacturer: str

    def log_to_influx(self):
        raise NotImplementedError

    def _read_last_line(self, filepath):
        with open(filepath, "r") as f:
            lastline = f.readlines()[-1]
        return lastline.strip()


class BlueforsFridge(Fridge):
    def __init__(self, logging_device, setup, room, user, log_folder, manufacturer):
        super().__init__(logging_device, setup, room, user, log_folder, manufacturer)
        self._regex_dict = {
            "temperature_K": r"CH[0-9] T",
            "resistance_Ohm": r"CH[0-9] R",
            "binary_state": r"Channels ",
            "flow_mol_per_s": r"Flowmeter ",
            "power_W": r"Heaters ",
            "pressure_Pa_abs": r"maxigauge ",
        }
        self._SI_unitconverter = {
            "temperature_K": 1.0,
            "resistance_Ohm": 1.0,
            "binary_state": 1,  # keep it an integer for the bool
            "flow_mol_per_s": 1e-3,
            "power_W": 1.0,
            "pressure_Pa_abs": 100,  # mbar to Pa
        }
        self._pressure_assignement = {
            "CH1": "p1_OVC",
            "CH2": "p2_still_pressure",
            "CH3": "p3_condensing_pressure",
            "CH4": "p4_forepump_backpressure",
            "CH5": "p5_dump_pressure",
            "CH6": "p6_serviceline_pressure",
        }
        self._temperature_assignement = {
            "CH1": "50K_flange",
            "CH2": "4K_flange",
            "CH3": "magnet",
            "CH5": "still_flange",
            "CH6": "mxc_flange",
        }

        self._heater_assignement = {0: "mxc_heater", 1: "still_heater"}

        self.influx_handle = InfluxDB()
        self.msmnts = Measurements(self.influx_handle)

    @classmethod
    def _singleMeasurement(self):
        return {"temperature_K", "resistance_Ohm", "flow_mol_per_s"}

    @classmethod
    def _ommitMeasurement(self):
        return {"resistance_Ohm"}

    def _package_heaters(self, key, value, filename):
        split = value.split(",")
        split = np.reshape(split, (2, 2))
        for i, line in enumerate(split):
            self._create_single_measurement(key, line[1], self._heater_assignement[i])
        return

    def _package_pressures(self, key, value, filename):
        split = value.split(",")[:-1]
        split = np.reshape(split, (6, 6))
        for line in split:
            self._create_single_measurement(
                key, line[3], self._pressure_assignement[line[0]]
            )
        return

    def _package_binary(self,  key,value):
        value = value[2:]
        value = value.split(",")
        for line in value:
            self._create_single_measurement(key,line[1],line[0])
       

    def _package_temperatures_resistances(self, key, value, filename):
        # find out witch measurement
        mtch = re.match(self._regex_dict[key], filename)
        position = self._temperature_assignement[mtch.group(0)[:3]]

        self._create_single_measurement(key, value, position)

    def _package_flow(self, key, value):
        position = "flow_after_coldtrap"
        self._create_single_measurement(key, value, position)

    def _create_measurements(self, key, value, filename):

        if key in self._ommitMeasurement():
            print("We dont store that value")
            return

        if key == "temperature_K":
            print("We do a temperature measurement ")
            self._package_temperatures_resistances(key, value, filename)

        if key == "power_W":
            self._package_heaters(key, value, filename)

        if key == "pressure_Pa_abs":
            self._package_pressures(key, value, filename)

        if key == "flow_mol_per_s":
            self._package_flow(key, value)
        if key == "binary_state": 
            self._package_binary(key,value)
        return


    def _create_single_measurement(self, key, value, position):
        m = dict()
        tags = dict()
        fields = dict()

        m["measurement"] = self.logging_device

        tags["room"] = self.room
        tags["user"] = self.user
        tags["setup"] = self.setup
        tags["quality"] = "testDeleteLater"
        tags["position"] = position

        if key == "binary_state":
            fields[key] = bool(int(value) * self._SI_unitconverter[key])
        else:
            fields[key] = float(value) * self._SI_unitconverter[key]

        m["tags"] = tags
        m["fields"] = fields

        print("Print we are ready to append the following")
        print(m)
        self.msmnts.append(m)
        return

    def log_to_influx(self, path):
        directory, filename = os.path.split(path)
        print(filename)
        key = self._match_filename(filename)
        line = self._read_last_line(filepath=path)
        Date, Time, val = line.split(",", 2)
        self._create_measurements(key, val, filename)
        self.msmnts.upload_to_influx()

        return

    def _match_filename(self, filename):
        for key, value in self._regex_dict.items():
            if not re.match(value, filename):
                continue
            if re.match(value, filename):
                return key


class Measurements:
    def __init__(self, influx_handle: InfluxDB) -> None:
        self.measurements = []
        self.influx_handle = influx_handle
        self._influxFieldKeyDict = {  # Zahlenwerte
            "temperature_C": None,
            "temperature_K": None,
            "pressure_Pa_rel": None,
            "pressure_Pa_abs": None,
            "resistance_Ohm": None,
            "flow_m3_per_s": None,
            "flow_mol_per_s": None,
            "powerOutage_s": None,
            "uptime_s": None,
            "binary_state": None,  # True False
            "humidity_pRH": None,
            "power_W": None,
        }

        self._influxTagKeyDict = {
            "room": ["B15", "B16", "B17", "C17"],
            "setup": ["sofia", "tabea", "fritz", "charlie", "broker"],
            "position": None,  # z.B. "N2 exhaust tube"
            "user": ["pmaerki", "benekrat", "baehler", "lostertag"],
            "quality": ["testDeleteLater", "use"],
        }

    def append(self, dict_data: dict):
        # Check if valid an d then append
        # self.__assert_valid(dict_data)
        self._assert_valid(dict_data)
        self.measurements.append(dict_data)

    def upload_to_influx(self):
        # Check the connection
        # try to upload
        if not self.measurements:
            print("Nothing to upload")
            return

        self.influx_handle.push_to_influx(self.measurements)
        self.measurements = []
        return

    def _assert_valid(self, measurement):
        for field_name in measurement["fields"]:
            assert (
                field_name in self._influxFieldKeyDict
            ), f"field '{field_name}' is not in {self._influxFieldKeyDict}"
        for tag_name, tag_value in measurement["tags"].items():
            valid_values = self._influxTagKeyDict[tag_name]
            if valid_values is None:
                continue
            assert (
                tag_value in valid_values
            ), f"{tag_name}={tag_value} is not in {valid_values}"


if __name__ == "__main__":
    f = BlueforsFridge(
        logging_device="Zorro",
        room="heaven",
        user="benekrat",
        log_folder="test",
        manufacturer="dreamfridges",
    )
