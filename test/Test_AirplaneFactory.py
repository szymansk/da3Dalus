import Airplane.AirplaneFactory as ap
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
import logging


CPACS_FILE_NAME = "aircombat_v14"

if __name__ == "__main__":

    logging.info(f"Start testing Airplane Factory with CPACS File {CPACS_FILE_NAME}")
    m = myDisplay.myDisplay.instance(True, 1, False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    test_class = ap.AirplaneFactory(tigl_h)
    test_class.create_airplane()

    logging.info("Test finished. Display Results")
    m.start()
