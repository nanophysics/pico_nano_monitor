import os
import time
from watch_dog import OnMyWatch
from utils import BlueforsFridge


def get_fridge() -> BlueforsFridge:
    username = os.environ["USERNAME"]

    fridge_name = {
        "Sofia_CryoPC": "sofia",
        "Tabea_CryoPC": "tabea",
    }[username]

    return BlueforsFridge(
        logging_device=f"bluefors_{fridge_name}",
        setup=fridge_name,
        room="B17",
        user="pmaerki",
        log_folder=rf"C:\Users\{username}\Bluefors logs",
        manufacturer="Bluefors",
    )


fridge = get_fridge()
if __name__ == "__main__":
    while True:
        try:
            wd = OnMyWatch(fridge)
            wd.run()
        except Exception as e:
            print(e)
            print("Restarting in 10s")
            time.sleep(10.0)
