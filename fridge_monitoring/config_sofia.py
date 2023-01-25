from utils import BlueforsFridge

def get_fridge() -> BlueforsFridge:
    fridge = BlueforsFridge(
        setup_name= 'Sofia', 
        room= 'B17',
        user= 'benekrat',
        log_folder = r"C:\Users\Benedikt\Documents\BFWatcher\directory_to_watch",
        manufacturer = 'Bluefors')

    return fridge



if __name__ == '__main__':
    sofia = get_fridge()

