from dataclasses import dataclass
import os
import re
import pathlib
import numpy as np
from influxdb_fridges import InfluxDB


class BlueforsFridge:
    def __init__(self,     logging_device: str,
    setup: str,
    room: str,
    user: str,
    log_folder: pathlib.Path,
    manufacturer: str,
)-> None:
        assert isinstance(log_folder, pathlib.Path)

        self.logging_device=logging_device
        self.setup = setup
        self.room = room
        self.user = user
        self.log_folder = log_folder
        self.manufacturer = manufacturer

        self._regex_dict = {
            "temperature_K": "CH[0-9] T",
            "resistance_Ohm": "CH[0-9] R",
            "binary_state": "Channels ",
            "flow_mol_per_s": "Flowmeter ",
            "power_W": "Heaters ",
            "pressure_Pa_abs": "maxigauge ",
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
    def _singleMeasurement(cls) -> set[str]:
        return {"temperature_K", "resistance_Ohm", "flow_mol_per_s"}

    @classmethod
    def _ommitMeasurement(cls) -> set[str]:
        return {"resistance_Ohm"}

    def _read_last_line(self, filename):
        with filename.open("r") as f:
            lastline = f.readlines()[-1]
        return lastline.strip()

    def _package_heaters(
        self, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        split = value.split(",")
        split = np.reshape(split, (2, 2))
        for i, line in enumerate(split):
            self._create_single_measurement(
                dimension, line[1], self._heater_assignement[i]
            )

    def _package_pressures(
        self, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        split = value.split(",")[:-1]
        split = np.reshape(split, (6, 6))
        for line in split:
            self._create_single_measurement(
                dimension, line[3], self._pressure_assignement[line[0]]
            )
        return

    def _package_binary(self, dimension: str, value: str) -> None:
        value = value[2:]
        value = value.split(",")
        value = np.reshape(value, (32, 2))
        for line in value:
            self._create_single_measurement(dimension, line[1], line[0])

    def _package_temperatures_resistances(
        self, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        # find out witch measurement
        match = re.match(self._regex_dict[dimension], filename.name)
        position = self._temperature_assignement[match.group(0)[:3]]

        self._create_single_measurement(dimension, value, position)

    def _package_flow(self, dimension: str, value: str) -> None:
        position = "flow_after_coldtrap"
        self._create_single_measurement(dimension, value, position)

    def _create_measurements(
        self, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        if dimension in self._ommitMeasurement():
            print("We dont store that value")
            return

        if dimension == "temperature_K":
            print("We do a temperature measurement ")
            self._package_temperatures_resistances(dimension, value, filename)

        if dimension == "power_W":
            self._package_heaters(dimension, value, filename)

        if dimension == "pressure_Pa_abs":
            self._package_pressures(dimension, value, filename)

        if dimension == "flow_mol_per_s":
            self._package_flow(dimension, value)
        if dimension == "binary_state":
            self._package_binary(dimension, value)
        return

    def _create_single_measurement(self, dimension: str, value: str, position):
        m = dict()
        tags = dict()
        fields = dict()

        m["measurement"] = self.logging_device

        tags["room"] = self.room
        tags["user"] = self.user
        tags["setup"] = self.setup
        tags["quality"] = "testDeleteLater"
        tags["position"] = position

        if dimension == "binary_state":
            fields[dimension] = bool(int(value) * self._SI_unitconverter[dimension])
        else:
            fields[dimension] = float(value) * self._SI_unitconverter[dimension]

        m["tags"] = tags
        m["fields"] = fields

        print("Print we are ready to append the following")
        print(m)
        self.msmnts.append(m)
        return

    def log_to_influx(self, filename: pathlib.Path) -> None:
        print(filename)
        dimension = self._get_dimension(filename.name)
        if dimension is None:
            return
        try:
            line = self._read_last_line(filename=filename)
        except Exception as e:
            print(f"Ignore any error while reading the file {filename}: {e}")
            return
        _date, _time, val = line.split(",", 2)
        self._create_measurements(dimension, val, filename)
        self.msmnts.upload_to_influx()

    def _get_dimension(self, filename: str) -> str|None:
        """
        Returns
         "temperature_K", "resistance_Ohm", "binary_state"...
        """
        assert isinstance(filename, str)
        for key, value in self._regex_dict.items():
            if re.match(value, filename):
                return key
        return None


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
