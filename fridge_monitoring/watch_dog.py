from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging
from utils import Fridge
from typing import Type
import os 
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)

class HandleFileSystemEvents(FileSystemEventHandler):
    def __init__(self,fridge: Type[Fridge]):
        super()
        self.fridge = fridge


    # @staticmethod
    def on_any_event(self, event):
        # Filter out events we dont care specifically
        
        if event.event_type in ["deleted", "moved"]:
            logging.debug("File Moved")
            return
        if event.src_path is None or event.is_directory:
            logging.debug("Event has no path or is a path to a directory")
            return

        
        #directory, filename = os.path.split(event.src_path)
        self.fridge.log_to_influx(event.src_path)
        # we will have two event types to deal with, modified or created


class OnMyWatch:
    def __init__(self, fridge: Fridge):
        self.event_handler = HandleFileSystemEvents(fridge)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, fridge.log_folder, recursive=True)

    def run(self):
        self.observer.start()
        try:
            while True:
                time.sleep(10)
        except:
            self.observer.stop()
            self.observer.join()


if __name__ == "__main__":
    watch_dir = r"directory_to_watch"
    wd = OnMyWatch(watch_dir=watch_dir)
    wd.run()
