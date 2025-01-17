import logging
import pathlib
import typing
from bluefors import BlueforsFridge
from constants import MonitoringError

logger = logging.getLogger(__file__)


class FileObserver:
    def __init__(self, filename: pathlib.Path) -> None:
        self.filename = filename
        self.lineno = 0
        self.f = self.filename.open("r", encoding=None)
        # self.f.seek(0, os.SEEK_END)

    def follow_obsolete(self) -> typing.Optional[str]:
        # curr_position = self.f.tell()
        line = self.f.readline()
        assert isinstance(line, str)
        if line == "":
            # self.f.seek(curr_position)
            return None
        return line

    def close(self) -> None:
        self.f.close()

    def poll(self, fridge: BlueforsFridge) -> int:
        influx_count = 0
        while True:
            line = self.f.readline()
            assert isinstance(line, str)
            if line == "":
                return influx_count

            self.lineno += 1
            influx_count += fridge.log_influx_line(
                filename=self.filename,
                line=line,
                lineno=self.lineno,
            )


class FilesObserver:
    def __init__(self, day_directory: pathlib.Path) -> None:
        self.day_directory = day_directory
        self.files: dict[str, FileObserver] = {}

    def close(self) -> None:
        for f in self.files.values():
            f.close()

    def _discover_new_files(self) -> None:
        log_files1 = self.day_directory.glob("*.log")
        log_files2 = [d for d in log_files1 if d.is_file()]
        for log_file in log_files2:
            if log_file.name in self.files:
                # We already observer this file
                continue
            # The is a new logfile
            logger.info(
                f"A new file has appeared: {self.day_directory.name}/{log_file.name}"
            )
            self.files[log_file.name] = FileObserver(log_file)

    def poll(self, fridge: BlueforsFridge) -> int:
        self._discover_new_files()
        influx_count = 0
        for f in self.files.values():
            influx_count += f.poll(fridge=fridge)
        return influx_count


class DirectoryObserver:
    def __init__(self, fridge: BlueforsFridge) -> None:
        self.fridge = fridge
        logger.info(f"DirectoryObserver: {fridge.log_folder}")
        self.files_observer = FilesObserver(self._latest_day_directory)

    @property
    def _latest_day_directory(self) -> pathlib.Path:
        directories1 = self.fridge.log_folder.glob("*")
        directories2 = [d for d in directories1 if d.is_dir()]
        if len(directories2) == 0:
            raise MonitoringError(f"No directories found in {self.fridge.log_folder}")
        return sorted(directories2)[-1]

    def poll(self) -> None:
        influx_count = self.files_observer.poll(fridge=self.fridge)
        if influx_count > 0:
            logger.info(f"Measurements sent to influxdb: {influx_count}")
        new_day_directory = self._latest_day_directory
        if new_day_directory.name == self.files_observer.day_directory.name:
            return

        # A new day has started
        self.files_observer.close()
        logger.info(f"A new directory has appeared: {new_day_directory.name}")
        self.files_observer = FilesObserver(new_day_directory)
