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

from module.base.utils import get_color, crop, color_similar

class ConversionUnique(Dock):
    # checking if we are actually in gear page
    def is_in_gear(self):
        logger.info('checking if in gear')
        interval= Timer (3)
        interval.reached
        return SHIP_INFO_EQUIPMENT_CHECK.match(self.device.image)

    # closing augment popup
    def augment_popup_close(self, skip_first_screenshot=False):
        logger.info('Augment popup close')
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.is_in_gear():
                self.device.sleep(3)
                return
            if self.appear_then_click(AUGMENT_CANCEL, interval=3):
                continue
            if self.appear_then_click(AUGMENT_CANCEL2, interval=3):
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
                self.ui_goto_main()
                continue         
            if interval.reached() and self.is_in_gear():
                logger.info(f'is_in_gear -> Main')
                self.ui_goto_main()
                interval.reset()
                continue
            if self.is_in_main(interval=5):
                break

    def conv_uniq_menu(self, skip_first_screenshot=False):
        logger.hr('conversion menu', level=2)

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if AUGMENT_EMPTY.match(self.device.image):
                logger.info('No unique module to enhance')
                return False
                
            # if not AUGMENT_EMPTY.match(self.device.image) and AUGMENT_INGEAR_CONFIRM.match(self.device.image):
            #     self.device.click(AUGMENT_EMPTY)
            #     logger.info('clicking unique module')
            #     continue

            if not AUGMENT_EMPTY.match(self.device.image) and AUGMENT_INGEAR_CONFIRM.match(self.device.image):
                logger.warning('=== AUGMENT_EMPTY CLICK ANOMALY DETECTED ===')
                logger.warning(f'AUGMENT_EMPTY.match() returned: False')
                logger.warning(f'AUGMENT_INGEAR_CONFIRM.match() returned: True')
                logger.warning(f'About to click AUGMENT_EMPTY despite match failure')

                # Log template matching diagnostics
                logger.warning(f'AUGMENT_EMPTY template area: {AUGMENT_EMPTY.area}')
                logger.warning(f'AUGMENT_EMPTY button coordinates: {AUGMENT_EMPTY.button}')

                # Log the coordinates that will be generated
                try:
                    from module.base.utils import random_rectangle_point
                    test_x, test_y = random_rectangle_point(AUGMENT_EMPTY.button)
                    logger.warning(f'Generated click coordinates would be: ({test_x}, {test_y})')
                    
                    # Check if coordinates are within expected bounds
                    area_x1, area_y1, area_x2, area_y2 = AUGMENT_EMPTY.button
                    if area_x1 <= test_x <= area_x2 and area_y1 <= test_y <= area_y2:
                        logger.warning('Coordinates are within button bounds')
                    else:
                        logger.error(f'Coordinates ({test_x}, {test_y}) are OUTSIDE button bounds {AUGMENT_EMPTY.button}')
                        
                except Exception as e:
                    logger.error(f'Failed to generate test coordinates: {e}')
                
                logger.warning('=== END ANOMALY DETECTION ===')
                
                self.device.click(AUGMENT_EMPTY)
                logger.info('clicking unique module')
                continue

            if self.ui_page_appear(page_storage):
                self.appear_then_click(BACK_ARROW, interval=3)
                self.device.click(AUGMENT_EMPTY)
                continue

            if self.appear(MODULE_ENHANCE, interval=3):
                self.appear_then_click(AUGMENT_CANCEL, interval=3)
                self.device.click(AUGMENT_EMPTY)
                continue

            if self.appear(CONVT2_SELECT, interval=3):
                logger.info('convert appeared, clicking')
                self.device.click(CONVT2_SELECT)
                continue
            if CONVT2_MENU.match(self.device.image):
                logger.info('conversion menu arrived')
                return True  # Return True to indicate enhancement should proceed

    def conv_uniq_enhance(self, skip_first_screenshot=False):
        logger.hr('conversion enhancement', level=2)

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(CONVT2_MAX, interval=3):
                logger.hr('Conversion at max')
                self.augment_popup_close()
                return True
            
            if self.appear(CONVT2_START_COST, interval=3, similarity=1):
                logger.hr('added conversion stones')
                self.device.click(CONVT2_START_COST)
                continue

            if self.appear_then_click(CONVT2_START, interval=3):
                self.wait_until_appear_then_click(CONVT2_NEW)
                logger.hr('Confirm new stats')
                self.wait_until_appear_then_click(CONVT2_FINISH)
                logger.hr('Conversion attempt finished once')
                continue

    # def conv_uniq_cycle(self, skip_first_screenshot=False):
    #     logger.hr('Augment conversion: Uniques', level = 3)
    #     conv = False
    #     has_unique_equipped = False
    #     while 1:
    #         if skip_first_screenshot:
    #             skip_first_screenshot = False
    #         else:
    #             self.device.screenshot()

    #         if conv is True and self.appear(SHIP_DETAIL_CHECK):
    #             self.appear_then_click(BACK_ARROW, interval=3)
                    
    #         if self.appear(DOCK_CHECK, offset=(10)):
    #             return

    #         if self.is_in_gear() and conv is False and has_unique_equipped is False:
    #             logger.info('in gear, attempt enhancement')
    #             has_unique_equipped=self.conv_uniq_menu()

    #         if has_unique_equipped is True and conv is False:
    #             conv= self.conv_uniq_enhance()
            

    def conv_uniq_cycle(self, skip_first_screenshot=False):
        logger.hr('Augment conversion: Uniques', level = 3)
        conv = False
        has_unique_equipped = False
        back_arrow_attempts = 0
        max_back_arrow_attempts = 5  # Maximum attempts to click back arrow
        
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if conv is True and self.appear(SHIP_DETAIL_CHECK):
                logger.info(f'Ship detail detected, attempting back arrow (attempt {back_arrow_attempts + 1})')
                
                # Click back arrow once
                if self.appear_then_click(BACK_ARROW, interval=1):
                    back_arrow_attempts += 1
                    self.device.sleep(1.5)  # Brief pause to allow UI to respond
                    
                    # Immediately check if we've reached dock after this single click
                    self.device.screenshot()
                    if self.appear(DOCK_CHECK, offset=(30)):
                        logger.info('Successfully returned to dock after back arrow click')
                        back_arrow_attempts = 0
                        continue  # Exit this condition and let dock check handle it
                        
                    # If still in ship detail and haven't exceeded max attempts, continue loop to try again
                    if self.appear(SHIP_DETAIL_CHECK) and back_arrow_attempts < max_back_arrow_attempts:
                        logger.info(f'Still in ship detail after attempt {back_arrow_attempts}, will retry')
                        continue
                        
                    # If we're no longer in ship detail but also not in dock, something unexpected happened
                    if not self.appear(SHIP_DETAIL_CHECK) and not self.appear(DOCK_CHECK, offset=(30)):
                        logger.warning('Navigated to unexpected page, using fallback navigation')
                        self.appear_then_click(BACK_ARROW, interval=1)
                        back_arrow_attempts = 0
                        conv = False
                        has_unique_equipped = False
                        continue
                        
                    # If exceeded max attempts, use fallback
                    if back_arrow_attempts >= max_back_arrow_attempts:
                        logger.warning('Max back arrow attempts reached, trying alternative navigation')
                        self.appear_then_click(BACK_ARROW, interval=1)
                        back_arrow_attempts = 0
                        conv = False
                        has_unique_equipped = False
                        continue
                        
            if self.appear(DOCK_CHECK, offset=(30)):
                logger.info('In dock, cycle complete')
                return

            if self.is_in_gear() and conv is False and has_unique_equipped is False:
                logger.info('in gear, attempt enhancement')
                has_unique_equipped = self.conv_uniq_menu()

            if has_unique_equipped is True and conv is False:
                conv = self.conv_uniq_enhance()
                back_arrow_attempts = 0  # Reset counter when starting new enhancement

    # def verify_lmb(self):
    #     if LIMIT_MAX.match(self.device.image):
    #         logger.info('MAX LMB')
    #         return True
    #     elif self.appear(LIMIT_MAXRS):
    #         logger.info('MAX LMB')
    #         return True
    #     else:
    #         logger.info('LMB unknown')
    #         return False

    def verify_lmb(self):
        logger.info('=== LMB Verification Debug ===')
        
        # Take a fresh screenshot to ensure we have current data
        self.device.screenshot()
        
        # Debug LIMIT_MAX check
        logger.info('Checking LIMIT_MAX button...')
        try:
            limit_max_result = LIMIT_MAX.match(self.device.image)
            logger.info(f'LIMIT_MAX.match() result: {limit_max_result}')
            
            if limit_max_result:
                logger.info('MAX LMB detected via LIMIT_MAX.match()')
                return True
                
        except Exception as e:
            logger.error(f'Error checking LIMIT_MAX: {e}')
            logger.error(f'LIMIT_MAX object: {LIMIT_MAX}')
            if hasattr(LIMIT_MAX, 'area'):
                logger.info(f'LIMIT_MAX area: {LIMIT_MAX.area}')
            if hasattr(LIMIT_MAX, 'file'):
                logger.info(f'LIMIT_MAX file: {LIMIT_MAX.file}')
        
        # Debug LIMIT_MAXRS check
        logger.info('Checking LIMIT_MAXRS button...')
        try:
            # Use default similarity and threshold values for debugging
            limit_maxrs_result = self.appear(LIMIT_MAXRS, similarity=0.85, threshold=30)
            logger.info(f'self.appear(LIMIT_MAXRS) result: {limit_maxrs_result}')
            
            # Try with lower similarity
            limit_maxrs_low_sim = self.appear(LIMIT_MAXRS, similarity=0.7, threshold=30)
            logger.info(f'LIMIT_MAXRS with similarity=0.7: {limit_maxrs_low_sim}')
            
            # Try with higher threshold (more lenient)
            limit_maxrs_high_thresh = self.appear(LIMIT_MAXRS, similarity=0.85, threshold=50)
            logger.info(f'LIMIT_MAXRS with threshold=50: {limit_maxrs_high_thresh}')
            
            if limit_maxrs_result:
                logger.info('MAX LMB detected via LIMIT_MAXRS.appear()')
                return True
                
        except Exception as e:
            logger.error(f'Error checking LIMIT_MAXRS: {e}')
            logger.error(f'LIMIT_MAXRS object: {LIMIT_MAXRS}')
            if hasattr(LIMIT_MAXRS, 'area'):
                logger.info(f'LIMIT_MAXRS area: {LIMIT_MAXRS.area}')
            if hasattr(LIMIT_MAXRS, 'color'):
                logger.info(f'LIMIT_MAXRS expected color: {LIMIT_MAXRS.color}')
                # Get actual color from the area
                actual_color = get_color(self.device.image, LIMIT_MAXRS.area)
                logger.info(f'Actual color in LIMIT_MAXRS area: {actual_color}')
                # Calculate color difference
                color_diff = color_similar(actual_color, LIMIT_MAXRS.color, threshold=255)
                logger.info(f'Color similarity (higher is more similar): {color_diff}')
        
        # Additional debugging - crop the areas and save them for inspection
        try:
            if hasattr(LIMIT_MAX, 'area'):
                limit_max_crop = crop(self.device.image, LIMIT_MAX.area)
                logger.info(f'LIMIT_MAX area cropped, shape: {limit_max_crop.shape}')
                
            if hasattr(LIMIT_MAXRS, 'area'):
                limit_maxrs_crop = crop(self.device.image, LIMIT_MAXRS.area)
                logger.info(f'LIMIT_MAXRS area cropped, shape: {limit_maxrs_crop.shape}')
                
        except Exception as e:
            logger.error(f'Error cropping debug areas: {e}')
        
        logger.info('LMB status could not be determined - both checks failed')
        logger.info('=== End LMB Verification Debug ===')
        return False

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
        #self.dock_sort_method_dsc_set(wait_loading=False)
        extra = ['unique_augment_module']
        self.dock_filter_set(extra=extra)

        if self.appear(DOCK_EMPTY, offset=(20, 20)):
            logger.info('no ships with unique modules owned')
            return 'dock empty'
        
        # Iterate through all grid positions
        for x, y, button in CARD_GRIDS.generate():
            logger.info(f'Attempting to process ship at grid position ({x}, {y})')
            
            # Try to enter the ship - ship_info_enter will handle if there's no ship there
            try:                
                self.ship_info_enter(button, check_button=SHIP_DETAIL_CHECK, long_click=False)
                
                # If we get here, we successfully entered a ship
                logger.info(f'Successfully entered ship at grid position ({x}, {y})')

                # Go to LMB tab and verify max limit break
                self.ship_side_navbar_ensure(bottom=3)
                logger.info('Entered lmb tab, checking limit break status')
                
                # FIXED: Add parentheses to actually call the method
                max_lmb = self.verify_lmb()
                
                if max_lmb is True:
                    logger.info('Ship has max limit break, proceeding to gear tab')
                    # Go to gear tab
                    self.ship_side_navbar_ensure(bottom=2)
                    logger.info('Entered gear tab, processing ship')

                    self.conv_uniq_cycle()  # This already returns to dock
                    logger.info(f'Finished processing ship at grid position ({x}, {y})')

                else:
                    logger.info(f'Ship at ({x}, {y}) does not have max limit break, skipping')
                    self.appear_then_click(BACK_ARROW, interval=3)
                
            except Exception as e:
                # If ship_info_enter fails, it likely means no ship at this position
                logger.info(f'No ship or error at grid position ({x}, {y}): {str(e)[:100]}...')
                continue

        logger.info('Finished processing all grid positions')
        return 'finish'

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

        # Scheduler, 60day= 86400min
        self.config.task_delay(minute=86400)

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
