from utils import BlueforsFridge


def get_fridge() -> BlueforsFridge:
    fridge = BlueforsFridge(
        logging_device="bluefors_sofia",
        setup="sofia",
        room="B17",
        user="benekrat",
        log_folder=r"C:\Users\Sofia_CryoPC\Bluefors logs",
        manufacturer="Bluefors",
    )

    return fridge


if __name__ == "__main__":
    sofia = get_fridge()
