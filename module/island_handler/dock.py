from module.base.button import ButtonGrid
from module.base.decorator import cached_property, del_cached_property
from module.base.utils import random_rectangle_vector_opted
from module.island.ui import IslandUI
from module.island_handler.assets import *
from module.island_handler.dock_scanner import CharacterScanner
from module.logger import logger
from module.map_detection.utils import Points
from module.ui.switch import Switch

ISLAND_DOCK_SORTING = Switch('island_dock_sorting')
ISLAND_DOCK_SORTING.add_state('Ascending', check_button=ISLAND_DOCK_SORT_ASC,
                              click_button=ISLAND_DOCK_SORTING_CLICK, offset=(20, 5))
ISLAND_DOCK_SORTING.add_state('Descending', check_button=ISLAND_DOCK_SORT_DESC,
                              click_button=ISLAND_DOCK_SORTING_CLICK, offset=(20, 5))
ISLAND_DOCK_DETECT_AREA = (56, 128, 880, 561)
ISLAND_DOCK_DETECT = Button(ISLAND_DOCK_DETECT_AREA, color=(), button=ISLAND_DOCK_DETECT_AREA, name='ISLAND_DOCK_DETECT')
ISLAND_DOCK_CARD_ANCHOR_AREA = (11, 9, 29, 27)
ISLAND_DOCK_CARD_DELTA = (140, 180)
ISLAND_DOCK_CARD_SIZE = (124, 164)

class IslandDock(IslandUI):
    def is_in_island_dock(self):
        return self.appear(ISLAND_DOCK_CHECK, offset=(0, 20))

    def handle_island_dock_loading(self):
        # poor implementation, just wait for a while
        for _ in self.loop(timeout=0.6):
            pass

    def _island_dock_quit_check_func(self):
        return not self.appear(ISLAND_DOCK_CHECK, offset=(20, 20))

    def island_dock_quit(self):
        self.ui_back(check_button=self._island_dock_quit_check_func, skip_first_screenshot=True)

    def island_dock_sort_method_dsc_set(self, enable=True, wait_loading=True):
        if ISLAND_DOCK_SORTING.set('Descending' if enable else 'Ascending', main=self):
            if wait_loading:
                self.handle_island_dock_loading()

    def _get_dock_buttons(self):
        area = (ISLAND_DOCK_DETECT_AREA[0] + ISLAND_DOCK_CARD_ANCHOR_AREA[0],
                ISLAND_DOCK_DETECT_AREA[1] + ISLAND_DOCK_CARD_ANCHOR_AREA[1],
                ISLAND_DOCK_DETECT_AREA[2] - ISLAND_DOCK_CARD_SIZE[0] + ISLAND_DOCK_CARD_ANCHOR_AREA[2],
                ISLAND_DOCK_DETECT_AREA[3] - ISLAND_DOCK_CARD_SIZE[1] + ISLAND_DOCK_CARD_ANCHOR_AREA[3])
        image = self.image_crop(area, copy=True)
        anchors = TEMPLATE_ISLAND_DOCK_CARD_ANCHOR.match_multi(image, threshold=5)
        logger.attr('cards_in_view', len(anchors))
        rows = Points([(0., a.area[1]) for a in anchors]).group(threshold=5)
        return rows

    @cached_property
    def dock_grid(self):
        for _ in self.loop(timeout=2):
            grid = self.get_dock_grid()
            if len(grid.buttons) >= 6:
                return grid
        return grid

    def get_dock_grid(self):
        rows = self._get_dock_buttons()
        count = len(rows)
        if count >= 3:
            logger.warning(f'Unexpected card count in view: {count}, retrying detection')
            count = 0
        if count > 0:
            y_list = rows[:, 1]
            origin_y = y_list.min() + ISLAND_DOCK_DETECT_AREA[1]
        else:
            logger.warning('No cards detected, retrying detection')
            origin_y = 139

        grid = ButtonGrid(
            origin=(ISLAND_DOCK_DETECT_AREA[0], origin_y),
            delta=ISLAND_DOCK_CARD_DELTA,
            button_shape=ISLAND_DOCK_CARD_SIZE,
            grid_shape=(6, count),
            name='CARD'
        )
        return grid

    def next_dock_page(self, wait_loading=True):
        p1, p2 = random_rectangle_vector_opted((0, -250), box=ISLAND_DOCK_DETECT_AREA, padding=-10)
        self.device.drag(p1, p2, hold_duration=0.1, name='ISLAND_DOCK_NEXT_PAGE_SWIPE')
        del_cached_property(self, 'dock_grid')
        if wait_loading:
            self.handle_island_dock_loading()

    def prev_dock_page(self, wait_loading=True):
        p1, p2 = random_rectangle_vector_opted((0, 250), box=ISLAND_DOCK_DETECT_AREA, padding=-10)
        self.device.drag(p1, p2, hold_duration=0.1, name='ISLAND_DOCK_PREV_PAGE_SWIPE')
        del_cached_property(self, 'dock_grid')
        if wait_loading:
            self.handle_island_dock_loading()

    def ensure_dock_page_at_top(self):
        ISLAND_DOCK_DETECT.load_color(self.device.image)
        ISLAND_DOCK_DETECT._match_init = True
        drag_count = 0
        for _ in self.loop(timeout=10):
            self.prev_dock_page()
            drag_count += 1
            if self.appear(ISLAND_DOCK_DETECT, offset=(20, 20)):
                if drag_count >= 2:
                    logger.info('Reached top of dock page')
                    return True
            else:
                ISLAND_DOCK_DETECT.load_color(self.device.image)
                drag_count = 0
        return False

    def island_dock_select_one(self, button, skip_first=False):
        """
        Args:
            button (Button): Character button to select
            skip_first (bool):
        """
        for _ in self.loop(skip_first=skip_first):
            if self.is_button_selected(button, color=(19, 181, 231)):
                logger.info(f'Button {button.name} is selected')
                return True
            else:
                if self.appear(ISLAND_DOCK_CHECK, offset=(20, 20), interval=1):
                    self.device.click(button)
                continue

    def island_dock_select_confirm(self, check_button, skip_first=True):
        """
        Args:
            check_button (callable, Button):
            skip_first (bool):
        """
        for _ in self.loop(skip_first=skip_first):
            if self.ui_process_check_button(check_button):
                del_cached_property(self, 'dock_grid')
                break

            if self.appear_then_click(ISLAND_DOCK_CHARACTER_CONFIRM, offset=(20, 20), interval=2):
                continue

    def island_dock_select_manjuu(self):
        self.island_dock_sort_method_dsc_set(enable=False, wait_loading=True)
        # self.ensure_dock_page_at_top()  # not necessary for now since usually Manjuu is searched first
        scanner = CharacterScanner(self.dock_grid, identity=['Manjuu'], status='free')
        candidates = scanner.scan(self.device.image)
        if candidates:
            self.island_dock_select_one(candidates[0].button)
            return True
        else:
            logger.warning('No Manjuu found in dock')
            return False

    def island_dock_find_character(self, identity):
        self.ensure_dock_page_at_top()
        self.island_dock_sort_method_dsc_set(enable=True)
        ISLAND_DOCK_DETECT.load_color(self.device.image)
        ISLAND_DOCK_DETECT._match_init = True
        drag_count = 0
        for _ in self.loop(timeout=40, skip_first=False):
            # dock_grid needs refresh after each page swipe, so we need to get a new scanner each time
            scanner = CharacterScanner(self.dock_grid, identity=identity, status=None)
            candidates = scanner.scan(self.device.image)
            for candidate in candidates:
                if candidate.identity != identity:
                    continue
                return candidate
            self.next_dock_page()
            drag_count += 1
            if self.appear(ISLAND_DOCK_DETECT, offset=(20, 20)):
                if drag_count >= 2:
                    logger.warning('Reached end of dock page')
                    break
            else:
                ISLAND_DOCK_DETECT.load_color(self.device.image)
                drag_count = 0
        else:
            logger.warning('Failed to find all requested characters')
            return None

    def island_dock_find_character_with_blacklist(self, blacklist):
        self.ensure_dock_page_at_top()
        self.island_dock_sort_method_dsc_set(enable=True)
        ISLAND_DOCK_DETECT.load_color(self.device.image)
        ISLAND_DOCK_DETECT._match_init = True
        drag_count = 0
        for _ in self.loop(timeout=40, skip_first=False):
            # dock_grid needs refresh after each page swipe, so we need to get a new scanner each time
            scanner = CharacterScanner(self.dock_grid, identity='any', status='free')
            candidates = scanner.scan(self.device.image)
            candidates = (
                [c for c in candidates if c.grade == 'S']
                + [c for c in candidates if c.grade == 'A']
                + [c for c in candidates if c.grade == 'B']
                + [c for c in candidates if c.grade == 'C']
                + [c for c in candidates if c.grade == 'D']
                + [c for c in candidates if c.grade == 'E']
            )
            for candidate in candidates:
                if candidate.identity in blacklist:
                    logger.warning(f'Candidate {candidate.identity} is in blacklist, skip')
                    continue
                elif self.is_button_selected(candidate.button, color=(19, 181, 231)):
                    continue
                else:
                    return candidate
            self.next_dock_page()
            drag_count += 1
            if self.appear(ISLAND_DOCK_DETECT, offset=(20, 20)):
                if drag_count >= 2:
                    logger.warning('Reached end of dock page')
                    break
            else:
                ISLAND_DOCK_DETECT.load_color(self.device.image)
                drag_count = 0
        logger.warning('Failed to find any character not in blacklist')
        return None

    def island_dock_select_named_characters(self, identity_a, identity_b):
        """
        Search the dock in a single forward sweep for exactly two named
        characters, selecting each one immediately as it's found.
        """
        found = {identity_a: None, identity_b: None}
        self.ensure_dock_page_at_top()
        self.island_dock_sort_method_dsc_set(enable=True)
        ISLAND_DOCK_DETECT.load_color(self.device.image)
        ISLAND_DOCK_DETECT._match_init = True
        drag_count = 0
        for _ in self.loop(timeout=40, skip_first=False):
            scanner = CharacterScanner(
                self.dock_grid,
                identity=[i for i in (identity_a, identity_b) if found[i] is None],
                status=None
            )
            candidates = scanner.scan(self.device.image)
            for candidate in candidates:
                if found.get(candidate.identity) is None and candidate.identity in found:
                    found[candidate.identity] = candidate
                    if candidate.status == 'free':
                        self.island_dock_select_one(candidate.button)
            if all(v is not None for v in found.values()):
                break
            self.next_dock_page()
            drag_count += 1
            if self.appear(ISLAND_DOCK_DETECT, offset=(20, 20)):
                if drag_count >= 2:
                    logger.warning('Reached end of dock page')
                    break
            else:
                ISLAND_DOCK_DETECT.load_color(self.device.image)
                drag_count = 0
        else:
            missing = [k for k, v in found.items() if v is None]
            logger.warning(f'Failed to find all requested characters: {missing}')
        return found

    def extract_character_templates(self, folder_path='./assets/island/character/'):
        """
        must start in dock selection page, extract character templates,
        EN can name file after ocr results, other servers need manual renaming
        """
        import os
        from PIL import Image
        import re
        import unicodedata
        from module.ocr.ocr import Ocr
        from module.base.button import Button
        from module.island.assets import ISLAND_CLICK_SAFE_AREA

        if not self.is_in_island_dock():
            logger.warning('not in dock')
            return False
        
        self.ensure_dock_page_at_top()
        self.island_dock_sort_method_dsc_set(enable=True)
        os.makedirs(folder_path, exist_ok=True)
        
        # Get existing templates
        existing_templates = set()
        for filename in os.listdir(folder_path):
            if filename.endswith('.png'):
                name = filename[:-4].lower()
                existing_templates.add(name)
        logger.info(f'Found {len(existing_templates)} existing templates')
        
        # Check server
        is_en_server = getattr(self.config, 'SERVER', '').lower() == 'en'
        logger.info(f'Server: {self.config.SERVER}, Using OCR: {"Yes" if is_en_server else "No"}')
        
        # Name display area when a card is selected
        NAME_DISPLAY_AREA = (928, 91, 1252, 130)

        if is_en_server:
            name_button = Button(
                area=NAME_DISPLAY_AREA,
                color=(255, 255, 255),
                button=NAME_DISPLAY_AREA,
                name='CHARACTER_NAME'
            )
            name_ocr = Ocr(
                buttons=[name_button],
                lang='cnocr',
                letter=(255, 255, 255),
                threshold=128,
                name='SELECTED_CHARACTER_NAME'
            )
        
        TEMPLATE_AREA = (30, 16, 92, 66)
        
        def clean_character_name(raw_name):
            if not raw_name or not raw_name.strip():
                return None
            
            # Remove everything from "-L" or "–L" onward (including the -L)
            name = re.sub(r'[-–]L.*$', '', raw_name, flags=re.IGNORECASE)
            
            # Strip whitespace
            name = name.strip()
            
            if not name:
                return None
            
            # Normalize Unicode characters (é -> e, etc.)
            name = unicodedata.normalize('NFKD', name)
            name = ''.join(c for c in name if not unicodedata.combining(c))
            
            # Replace spaces and special characters with underscores
            name = re.sub(r'[^a-zA-Z0-9]', '_', name)  # Remove everything except letters and numbers
            name = re.sub(r'_+', '_', name)  # Collapse multiple underscores
            name = name.strip('_')
            
            return name
        
        extracted = 0
        skipped = 0
        
        # Use max 5 swipes/pages, may need adjustments in the future at some point
        MAX_PAGES = 5
        
        # Store identities from previous page to detect if page changed
        previous_identities = None
        
        for page in range(MAX_PAGES):
            logger.info(f'Processing page {page + 1}/{MAX_PAGES}')
            
            # Get all cards on current page
            scanner = CharacterScanner(self.dock_grid, identity='any', status=None)
            characters = scanner.scan(self.device.image, cached=False, output=False)
            
            if not characters:
                logger.info('No characters found on current page')
                break
            
            # Get current page identities for comparison
            current_identities = [char.identity for char in characters]
            
            # Check if page actually changed (only after first page)
            if previous_identities is not None:
                # Check if all characters are the same (page didn't change)
                if current_identities == previous_identities:
                    logger.info('Page content identical to previous page - reached end of dock')
                    break
                
                # Also check if there's significant overlap
                overlap_count = sum(1 for id1 in current_identities if id1 in previous_identities)
                overlap_ratio = overlap_count / max(len(current_identities), len(previous_identities))
                if overlap_ratio > 0.8 and len(current_identities) == len(previous_identities):
                    logger.info(f'High overlap ({overlap_ratio:.1%}) with previous page - reached end of dock')
                    break
            
            # Process each character
            for char in characters:
                # Quick identity check
                if char.identity and char.identity != 'unknown':
                    if char.identity.lower() in existing_templates:
                        skipped += 1
                        continue
                
                # Get filename based on server
                filename = None
                should_save = False
                
                if is_en_server:
                    # EN Server: Use OCR for name
                    self.device.click(char.button)
                    self.device.sleep(0.2)
                    self.device.screenshot()
                    
                    ocr_results = name_ocr.ocr(self.device.image)
                    
                    clean_name = clean_character_name(ocr_results)
                    
                    if clean_name:
                        logger.info(f'Cleaned name: "{clean_name}"')
                        
                        if clean_name.lower() not in existing_templates:
                            should_save = True
                            filename = f'{clean_name}.png'
                        else:
                            logger.info(f'Skipping existing: {clean_name}')
                    elif char.identity and char.identity != 'unknown':
                        # Fallback to identity if OCR fails
                        if char.identity.lower() not in existing_templates:
                            should_save = True
                            filename = f'{char.identity}.png'
                            logger.info(f'OCR failed, using identity: {char.identity}')
                    
                    self.device.click(ISLAND_CLICK_SAFE_AREA)
                    self.device.sleep(0.3)
                    
                else:
                    # Non-EN Server: Use identity only
                    if char.identity and char.identity != 'unknown':
                        if char.identity.lower() not in existing_templates:
                            should_save = True
                            filename = f'{char.identity}.png'
                        else:
                            logger.info(f'Skipping existing: {char.identity}')
                    else:
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:21]
                        should_save = True
                        filename = f'UNKNOWN_{timestamp}.png'
                
                # Save if needed
                if should_save and filename:
                    card_area = char.button.area
                    template_area = (
                        card_area[0] + TEMPLATE_AREA[0],
                        card_area[1] + TEMPLATE_AREA[1],
                        card_area[0] + TEMPLATE_AREA[2],
                        card_area[1] + TEMPLATE_AREA[3]
                    )
                    
                    img_np = self.image_crop(template_area, copy=True)
                    Image.fromarray(img_np).save(os.path.join(folder_path, filename))
                    
                    existing_templates.add(filename[:-4].lower())
                    extracted += 1
                    logger.info(f'Saved: {filename}')
                else:
                    skipped += 1
            
            # Store current identities for next iteration comparison
            previous_identities = current_identities
            
            # Don't swipe on the last page
            if page == MAX_PAGES - 1:
                logger.info('Reached maximum page limit')
                break
            
            # Try to swipe to next page
            logger.info(f'Swiping to page {page + 2}')
            self.next_dock_page(wait_loading=True)
        
        logger.info(f'Extracted {extracted} new templates, skipped {skipped} existing')
        logger.info(f'Templates saved to: {folder_path}')
        self.ensure_dock_page_at_top()
        return True
