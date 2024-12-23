import os
import pathlib
import time
from bluefors import BlueforsFridge


def get_fridge() -> BlueforsFridge:
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


if __name__ == "__main__":
    fridge = get_fridge()
    for file in fridge.log_folder.glob("**/*.log"):
        fridge.log_to_influx(file)

    if False:
        while True:
            try:
                wd = OnMyWatch(fridge)
                wd.run()
            except Exception as e:
                print(e)
                print("Restarting in 10s")
                time.sleep(10.0)
