from __future__ import annotations
import datetime
import itertools
import logging
import time
import os
import re
import pathlib
from influxdb_fridges import InfluxDB
from constants import MonitoringWarning

logger = logging.getLogger(__file__)


class BlueforsFridge:
    _singleMeasurement = {
        "temperature_K",
        "resistance_Ohm",
        "flow_mol_per_s",
    }
    _ommitMeasurement = {
        "resistance_Ohm",
    }
    _regex_dict = {
        "temperature_K": "CH[0-9] T",
        "resistance_Ohm": "CH[0-9] R",
        "binary_state": "Channels ",
        "flow_mol_per_s": "Flowmeter ",
        "power_W": "Heaters ",
        "pressure_Pa_abs": "maxigauge ",
    }
    _SI_unitconverter = {
        "temperature_K": 1.0,
        "resistance_Ohm": 1.0,
        "binary_state": 1,  # keep it an integer for the bool
        "flow_mol_per_s": 1e-3,
        "power_W": 1.0,
        "pressure_Pa_abs": 100,  # mbar to Pa
    }
    _pressure_assignement = {
        "CH1": "p1_OVC",
        "CH2": "p2_still_pressure",
        "CH3": "p3_condensing_pressure",
        "CH4": "p4_forepump_backpressure",
        "CH5": "p5_dump_pressure",
        "CH6": "p6_serviceline_pressure",
    }
    _temperature_assignement = {
        "CH1": "50K_flange",
        "CH2": "4K_flange",
        "CH3": "magnet",
        "CH5": "still_flange",
        "CH6": "mxc_flange",
    }
    _heater_assignement = {
        0: "mxc_heater",
        1: "still_heater",
    }

    def __init__(
        self,
        logging_device: str,
        setup: str,
        room: str,
        user: str,
        log_folder: pathlib.Path,
        manufacturer: str,
    ) -> None:
        assert isinstance(log_folder, pathlib.Path)

        self.logging_device = logging_device
        self.setup = setup
        self.room = room
        self.user = user
        self.log_folder = log_folder
        self.manufacturer = manufacturer

        self.influx_db = InfluxDB()
        self.msmnts = Measurements(self.influx_db)

    def reset_influx_db(self) -> None:
        logger.info("reset_influx_db()")
        self.influx_db.close()
        self.influx_db = InfluxDB()

    @staticmethod
    def factory() -> BlueforsFridge:
        username = os.environ["USERNAME"]
        log_folder = os.environ.get("BLUEFORS_LOGS_FOLDER", None)
        if log_folder is None:
            log_folder = rf"C:\Users\{username}\Bluefors logs"

        fridge_name = {
            "Sofia_CryoPC": "sofia",
            "Tabea_CryoPC": "tabea",
            "maerki": "tabea",
        }[username]

        return BlueforsFridge(
            logging_device=f"bluefors_{fridge_name}",
            setup=fridge_name,
            room="B17",
            user="pmaerki",
            log_folder=pathlib.Path(log_folder),
            manufacturer="Bluefors",
        )

    def _read_last_line(self, filename):
        with filename.open("r") as f:
            lastline = f.readlines()[-1]
        return lastline.strip()

    def _package_heaters(
        self, meas_time: float, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        assert isinstance(meas_time, float)

        split1 = value.split(",")
        for i, v01 in enumerate(itertools.batched(split1, 2)):
            # print(i, v01[1])
            self._create_single_measurement(
                meas_time,
                dimension,
                v01[1],
                self._heater_assignement[i],
            )
        # if True:
        #     print("----------")
        #     split2 = np.reshape(split1, (2, 2))
        #     for i, line in enumerate(split2):
        #         print(i, line[1])
        #         self._create_single_measurement(
        #             dimension, line[1], self._heater_assignement[i]
        #         )

    def _package_pressures(
        self, meas_time: float, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        assert isinstance(meas_time, float)

        value1 = value.split(",")[:-1]
        for v012345 in itertools.batched(value1, 6):
            # print(v012345[3], v012345[0])
            self._create_single_measurement(
                meas_time,
                dimension,
                v012345[3],
                self._pressure_assignement[v012345[0]],
            )
        if False:
            value2 = np.reshape(value1, (6, 6))
            for line in value2:
                print(line[3], line[0])
                # self._create_single_measurement(
                #     dimension, line[3], self._pressure_assignement[line[0]]
                # )

    def _package_binary(self, meas_time: float, dimension: str, value: str) -> None:
        assert isinstance(meas_time, float)
        value1 = value[2:]
        value2 = value1.split(",")
        for v01 in itertools.batched(value2, 2):
            if len(v01) % 2 != 0:
                raise MonitoringWarning("Expected even count.")
            # print(v2, v1)
            self._create_single_measurement(meas_time, dimension, v01[1], v01[0])

        # value3 = np.reshape(value2, (32, 2))
        # for line in value3:
        #     print(line[1], line[0])
        #     self._create_single_measurement(dimension, line[1], line[0])

    def _package_temperatures_resistances(
        self, meas_time: float, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        assert isinstance(meas_time, float)

        # find out witch measurement
        match = re.match(self._regex_dict[dimension], filename.name)
        if match is None:
            raise MonitoringWarning()
        position = self._temperature_assignement[match.group(0)[:3]]

        self._create_single_measurement(meas_time, dimension, value, position)

    def _package_flow(self, meas_time: float, dimension: str, value: str) -> None:
        assert isinstance(meas_time, float)

        position = "flow_after_coldtrap"
        self._create_single_measurement(meas_time, dimension, value, position)

    def _create_measurements(
        self, meas_time: float, dimension: str, value: str, filename: pathlib.Path
    ) -> None:
        assert isinstance(meas_time, float)
        if dimension in self._ommitMeasurement:
            logger.debug(f"We dont store that value: {dimension}")
            return

        if dimension == "temperature_K":
            logger.debug("We do a temperature measurement ")
            self._package_temperatures_resistances(
                meas_time, dimension, value, filename
            )

        if dimension == "power_W":
            self._package_heaters(meas_time, dimension, value, filename)

        if dimension == "pressure_Pa_abs":
            self._package_pressures(meas_time, dimension, value, filename)

        if dimension == "flow_mol_per_s":
            self._package_flow(meas_time, dimension, value)

        if dimension == "binary_state":
            self._package_binary(meas_time, dimension, value)

    def _create_single_measurement(
        self, meas_time: float, dimension: str, value: str, position
    ):
        assert isinstance(meas_time, float)

        if dimension == "binary_state":
            dimension_value = bool(int(value) * self._SI_unitconverter[dimension])
        else:
            dimension_value = float(value) * self._SI_unitconverter[dimension]

        m = {
            "tags": {
                "room": self.room,
                "user": self.user,
                "setup": self.setup,
                "quality": "testDeleteLater",
                "position": position,
            },
            "measurement": self.logging_device,
            "fields": {dimension: dimension_value},
            "time": int(meas_time * 1e9),  # Corresponds to time.time_ns()
        }

        logger.debug("Print we are ready to append the following")
        logger.debug(m)
        self.msmnts.append(m)

    def log_influx_file(self, filename: pathlib.Path) -> None:
        logger.info(filename)
        dimension = self._get_dimension(filename.name)
        if dimension is None:
            return
        try:
            line = self._read_last_line(filename=filename)
        except Exception as e:
            logger.error(f"Ignore any error while reading the file {filename}: {e}")
            raise
            return

        self.log_influx_line(filename=filename, line=line, lineno=42)

    def log_influx_line(self, filename: pathlib.Path, line: str, lineno: int) -> int:
        try:
            dimension = self._get_dimension(filename.name)
            if dimension is None:
                return 0

            # Line: 09-12-24,00:00:10,9.459000e+00
            v012 = line.split(",", 2)
            if len(v012) != 3:
                raise MonitoringWarning("Expected 3 elements")

            _date, _time, val = v012
            meas_time_str = f"{_date}_{_time}"
            # meas_time_str: 09-12-24_00:00:10
            meas_time = datetime.datetime.strptime(meas_time_str, "%d-%m-%y_%H:%M:%S")
            meas_time_stamp = meas_time.timestamp()
            diff_s = meas_time_stamp - time.time()
            assert abs(diff_s) < 48 * 3600
            self._create_measurements(meas_time_stamp, dimension, val, filename)
            return self.msmnts.upload_to_influx()

        except Exception as e:
            logger.error(f"{filename}({lineno}), line='{line}': exception={e!r}")
            logger.exception(e)
            raise e

    def _get_dimension(self, filename: str) -> str | None:
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
    _influxFieldKeyDict = {  # Zahlenwerte
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
    _influxTagKeyDict = {
        "room": ["B15", "B16", "B17", "C17"],
        "setup": ["sofia", "tabea", "fritz", "charlie", "broker"],
        "position": None,  # z.B. "N2 exhaust tube"
        "user": ["pmaerki", "benekrat", "baehler", "lostertag"],
        "quality": ["testDeleteLater", "use"],
    }

    def __init__(self, influx_handle: InfluxDB) -> None:
        self.measurements: list[dict] = []
        self.influx_handle = influx_handle

    def append(self, dict_data: dict):
        # Check if valid an d then append
        # self.__assert_valid(dict_data)
        self._assert_valid(dict_data)
        self.measurements.append(dict_data)

    def upload_to_influx(self) -> int:
        # Check the connection
        # try to upload
        measurement_count = len(self.measurements)
        if measurement_count == 0:
            return 0

        self.influx_handle.push_to_influx(self.measurements)
        self.measurements = []

        return measurement_count

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
