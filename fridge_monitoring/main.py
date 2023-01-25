import fridge_config 
from watch_dog import OnMyWatch

fridge = fridge_config.get_fridge()
wd = OnMyWatch(fridge)
if __name__ == "__main__": 
    wd.run()
