from module.augment.assets import *
from module.base.timer import Timer
#from module.base.base import ModuleBase
from module.exception import ScriptError
from module.logger import logger
from module.ocr.ocr import Ocr, Digit
from module.retire.dock import CARD_GRIDS, DOCK_EMPTY, Dock, SHIP_DETAIL_CHECK
from module.equipment.equipment import *
from module.equipment.assets import SHIP_INFO_EQUIPMENT_CHECK, SWIPE_AREA
from module.ui.assets import BACK_ARROW
from module.ui.page import page_dock, page_main, page_storage

class ConversionUnique(Dock):
    # checking if we are actually in gear page
    def is_in_gear(self):
        logger.info('checking if in gear')
        interval= Timer (3)
        interval.reached
        return AUGMENT_INGEAR_CONFIRM.match(self.device.image) and SHIP_INFO_EQUIPMENT_CHECK.appear_on(self.device.image)

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

    def not_appear_then_click(self, button, checkbutton, offset=0, interval=3, similarity=0.85, threshold=50):
        button = self.ensure_button(button)
        appear = self.appear(button, offset=offset, interval=interval, similarity=similarity, threshold=threshold)
        checkbutton = Ocr(checkbutton, lang='cnocr')
        checkappear = checkbutton.ocr(self.device.image)
        #rework, image matching did not detect checkbutton due to random backgrounds, was inconsistent
        #checkbutton = self.ensure_button(checkbutton)
        #checkappear = self.appear(checkbutton, offset=offset, interval=interval, similarity=similarity, threshold=threshold)
        if not appear and checkappear:  #click when its a augment module slot that is not empty
            self.device.click(button)
        return

    #one cycle of augment enhancing
    def conv_uniq_enhance(self, skip_first_screenshot=False):
        logger.hr('Enhance unique module', level=2)

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if AUGMENT_EMPTY.match(self.device.image):
                logger.info('No unique module to enhance')
                return
                
            if self.not_appear_then_click(AUGMENT_EMPTY, AUGMENT_INGEAR_CONFIRM, interval=3):
                logger.info('clicking unique module')
                continue

            if self.ui_page_appear(page_storage):
                self.device.click(BACK_ARROW)
                continue

            # if self.appear(MODULE_ENHANCE):
            #     self.device.click(AUGMENT_CANCEL)
            #     continue

            if self.appear(CONVT2_SELECT, interval=3):
                logger.info('convert appeared, clicking')
                self.device.click(CONVT2_SELECT)
                continue

            if CONVT2_MAX.match(self.device.image):
                logger.hr('Conversion at max')
                self.augment_popup_close()
                return
            
            if self.appear(CONVT2_START_COST, interval=3, similarity=1):
                logger.hr('added conversion stones')
                self.device.click(CONVT2_START_COST)
                while 1:
                    if CONVT2_START_COST_CONFIRM.match(self.device.image):
                        return
                    else:
                        self.device.click(CONVT2_START_COST)
                        continue
                continue

            if self.appear_then_click(CONVT2_START, interval=3):
                self.wait_until_appear_then_click(CONVT2_NEW)
                logger.hr('Confirm new stats')
                self.wait_until_appear_then_click(CONVT2_FINISH)
                logger.hr('Conversion attempt finished once')
                continue
                    
    def _confirm_swipe_result(self, attempts=3, delay=0.5):
        """Verify swipe result with multiple screenshots to reduce flukes."""
        mismatch_count = 0
        for _ in range(attempts):
            self.device.screenshot()
            if not SWIPE_CHECK.match(self.device.image):
                mismatch_count += 1
            self.device.sleep(delay)  # Wait for stable
        # Return False if most checks disagree (->new ship)
        return mismatch_count < (attempts // 2)

    def _ship_view_swipe(self, distance, check_button=AUGMENT_INGEAR_CONFIRM, swipe_delay=2):
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
                skip_first_screenshot = True
                while 1:
                    if skip_first_screenshot:
                        skip_first_screenshot = False
                    else:
                        self.device.screenshot()
                    if self.appear(check_button, offset=(30, 30), interval=swipe_delay):
                        break
                swipe_count += 1

            self.device.screenshot()

            #more swipe checks to make sure
            swipe_result = self._confirm_swipe_result(attempts=3, delay=0.5)
            
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
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.is_in_gear():
                logger.info('in gear, attempt enhancement')
                self.conv_uniq_enhance()
                
                # Swipe and check result
                swipe_result = self._ship_view_swipe(-400)
                if swipe_result is True:
                    logger.info('New ship detected, restarting cycle')
                    continue
                elif swipe_result is False:
                    logger.info('Same ship on multiple swipes, stopping')
                    break
                else:
                    logger.warning('Unexpected swipe result, stopping')
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
#python -m module.augment.conversion_unique
# ================================================
if __name__ == '__main__':
    # Force English server
    import module.config.server as server
    server.server = 'en'

    # use config x
    az = ConversionUnique('alasdebug', task='Augment') 

    # Force enable the augment conversion
    az.config.Augment_ConversionUnique = True  # Directly modify the config


    # start from mainscreen
    
    # 2. Run
    try:
        logger.info("Starting full live test...")
        az.run()  # This will execute the complete cycle
        logger.info("Full test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
