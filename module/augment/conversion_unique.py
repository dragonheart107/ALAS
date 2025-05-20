from module.augment.assets import *
from module.base.timer import Timer
#from module.base.base import ModuleBase
from module.exception import ScriptError
from module.logger import logger
#from module.ocr.ocr import Digit
from module.retire.dock import CARD_GRIDS, DOCK_EMPTY, Dock, SHIP_DETAIL_CHECK
from module.equipment.equipment import *
from module.equipment.assets import SHIP_INFO_EQUIPMENT_CHECK, SWIPE_AREA
from module.ui.assets import BACK_ARROW
from module.ui.page import page_dock, page_main

class ConversionUnique(Dock):
    # checking if we are actually in gear page
    def is_in_gear(self):
        interval= Timer (3)
        interval.reached
        return AUGMENT_INGEAR_CONFIRM.appear_on(self.device.image) and SHIP_INFO_EQUIPMENT_CHECK.appear_on(self.device.image)

    # closing augment popup
    def augment_popup_close(self, skip_first_screenshot=False):
        logger.info('Augment popup close')
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.is_in_gear():
                return
            if self.appear_then_click(AUGMENT_CANCEL):
                continue
            if self.appear_then_click(AUGMENT_CANCEL2):
                continue

    #get out of gear or dock to main page
    def augment_exit(self, skip_first_screenshot=False):
        """
        Pages:
            in: is_in_gear or dock
            out: MAIN
        """
        logger.info('Gear exit')
        interval = Timer(3)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.ui_page_appear(page_dock):
                logger.info(f'Gear exit at {page_dock}')
                continue         
            if interval.reached() and self.is_in_gear():
                logger.info(f'is_in_gear -> {BACK_ARROW}')
                self.device.click(BACK_ARROW)
                self.device.click(BACK_ARROW)
                interval.reset()
                continue
            if self.is_in_main(interval=5):
                break

    def not_appear_then_click(self, button, checkbutton, offset=0, interval=3, similarity=0.85, threshold=30):
        button = self.ensure_button(button)
        checkbutton = self.ensure_button(checkbutton)
        appear = self.appear(button, offset=offset, interval=interval, similarity=similarity, threshold=threshold)
        checkappear = self.appear(checkbutton, offset=offset, interval=interval, similarity=similarity, threshold=threshold)
        if not appear and checkappear:  # Execute click when appear is False and checkappear is True
            self.device.click(button)
        return

    #one cycle of augment enhancing
    def conv_uniq_enhance(self, skip_first_screenshot=False):
        logger.hr('Enhance unique module', level=2)
        while not self.appear(AUGMENT_EMPTY):

            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            self.not_appear_then_click(AUGMENT_EMPTY, AUGMENT_INGEAR_CONFIRM)
            logger.hr('Unique module found', level=2)
            self.wait_until_appear_then_click(CONVT2_SELECT)
            # logger.hr('waiting for convert to appear')
            # if self.appear(CONVT2_SELECT):
            #     logger.hr('Convertible module found,entering conversion menu', level=2)
            #     self.device.click(CONVT2_SELECT)
            #     continue #doesn't actually enter; clicks too fast, wont get recognized by game
            self.wait_until_appear(CONVT2_MENU)
            while 1:
                if skip_first_screenshot:
                    skip_first_screenshot = False 
                else:
                    self.device.screenshot()

                #augment already has max conversion
                if self.appear(CONVT2_MAX):
                    logger.hr('Conversion at max')
                    self.augment_popup_close()
                    logger.info('finished conversion for this ship, closing conversion')
                    return 
                #actual conversion enhancing part
                if self.appear(CONVT2_START):
                    logger.hr('Conversion start')
                    self.appear_then_click(CONVT2_START_COST)
                    self.appear_then_click(CONVT2_START)
                    self.appear_then_click(CONVT2_NEW)
                    continue
                #when already enhanced but augment not yet max
                if self.appear_then_click(CONVT2_FINISH):
                    logger.hr('Conversion in progress, one cycle finished')
                    continue
        else:
            return
                    
    def _ship_view_swipe(self, distance, check_button=AUGMENT_INGEAR_CONFIRM, swipe_delay=3):
        swipe_count = 0
        swipe_timer = Timer(5, count=10)
        self.handle_info_bar()
        SWIPE_CHECK.load_color(self.device.image)
        SWIPE_CHECK._match_init = True  # Disable ensure_template() on match(), allows ship to be properly determined
        # whether actually different or not
        while 1:
            if not swipe_timer.started() or swipe_timer.reached():
                swipe_timer.reset()
                self.device.swipe_vector(vector=(distance, 0), box=SWIPE_AREA.area, random_range=SWIPE_RANDOM_RANGE,
                                         padding=0, duration=(0.1, 0.12), name='SHIP_SWIPE')
                # self.wait_until_appear(check_button, offset=(30, 30))
                skip_first_screenshot = True
                while 1:
                    if skip_first_screenshot:
                        skip_first_screenshot = False
                    else:
                        self.device.screenshot()
                    # Use `interval=swipe_delay` to enforce a delay before next swipe
                    if self.appear(check_button, offset=(30, 30), interval=swipe_delay):
                        break
                swipe_count += 1

            self.device.screenshot()

            swipe_result = SWIPE_CHECK.match(self.device.image)  # Capture the match result

            if swipe_result:
                if swipe_count > 1:
                    logger.info('Same ship on multiple swipes')
                    return False
                continue

            if self.appear(check_button, offset=(30, 30), interval=swipe_delay) and not swipe_result:
                logger.info('New ship detected on swipe')
                return True

    def conv_uniq_cycle(self, skip_first_screenshot=False):
        logger.hr('Augment conversion: Uniques', level = 3)
        interval =Timer(3)
        while interval.reached():
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.is_in_gear():
                self.conv_uniq_enhance()
                if self._ship_view_swipe(-400) is True:
                    logger.info('new ship on swipe,restart cycle')
                    continue
                if self._ship_view_swipe(-400) is False:
                    logger.info('same ship on multiple swipes, stopping')
                    break

    def conv_uniq_run(self):
        """
        Navigation towards menu in order to enhance unique augments only and exit after

        Returns:
            str: 'dock empty', 'finish', 'timeout'

        Pages:
            in: Any
            out: page_dock
        """
        logger.hr('Unique augment conversion run', level=1)
        self.ui_ensure(page_dock)
        self.dock_favourite_set(wait_loading=False)
        self.dock_sort_method_dsc_set(wait_loading=False)
        extra = ['unique_augment_module']
        self.dock_filter_set(extra=extra)

        if self.appear(DOCK_EMPTY, offset=(20, 20)):
            logger.info('no ships with unique modules owned')
            return
        
        else:
            self.ship_info_enter(CARD_GRIDS[(0, 0)], check_button=SHIP_DETAIL_CHECK, long_click=False)
            logger.info('dock was not empty, entered ship, attempt to go to gear tab of ship')
            self.ship_side_navbar_ensure(bottom=2)
            logger.info('entered gear tab, going to cycle')
            self.conv_uniq_cycle()

    def run(self):
        if self.config.SERVER not in ['en']:
            logger.error(f'Task "Augment" is not available on server {self.config.SERVER} yet, '
                         f'please contact server maintainers')
            self.config.task_stop()

        if self.config.Augment_ConversionUnique == True:
            self.conv_uniq_run()
            self.augment_exit()
        else:
            raise ScriptError(f'Tried to run an yet undeveloped/unknown Augment Task')

        # Reset dock filters
        logger.hr('Augment run exit', level=1)
        self.dock_filter_set(wait_loading=False)

        # Scheduler
        self.config.task_stop(message= 'Augment Task Conversion_unique has finished')

# ================================================
# Live Testing Section - Add to bottom of your file
#python -m module.augment.conversion_unique
# ================================================
if __name__ == '__main__':
    # Force English server
    import module.config.server as server
    server.server = 'en'

    # Initialize with your actual config (not template)
    az = ConversionUnique('alasdebug', task='Augment') 

    # Force enable the augment conversion
    az.config.Augment_ConversionUnique = True  # Directly modify the config


    # # 1. First ensure you're at the main screen
    # az.device.screenshot()
    # if not az.is_in_main():
    #     logger.warning("Please manually navigate to game main screen")
    #     exit()
    
    # 2. Run the complete workflow
    try:
        logger.info("Starting full live test...")
        az.run()  # This will execute the complete cycle
        logger.info("Full test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
