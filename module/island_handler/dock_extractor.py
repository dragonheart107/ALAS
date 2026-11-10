"""Dev tool: save character card templates from the island dock.

Kept out of dock.py so that file can stay identical to upstream.

Open the dock character selection page in game, then run:
    python -m module.island_handler.dock_extractor

EN server names the files after the OCR result of the selected card's name.
Other servers save unknown cards as UNKNOWN_<timestamp>.png, rename them by hand.
Cards already recognised by a template in the folder are skipped.
"""
import os
import re
import unicodedata
from datetime import datetime

from PIL import Image

from module.base.button import Button
from module.base.utils import crop
from module.island.assets import ISLAND_CLICK_SAFE_AREA
from module.island_handler.dock import IslandDock
from module.logger import logger
from module.ocr.ocr import Ocr

TEMPLATE_FOLDER = './assets/island/character/'
# Name display area when a card is selected
NAME_DISPLAY_AREA = (928, 91, 1252, 130)
# Part of the card saved as the identity template, relative to the card
TEMPLATE_AREA = (30, 16, 92, 66)


def clean_character_name(raw_name):
    """
    Args:
        raw_name (str): OCR result of the name panel, e.g. 'Saint Louis-Lv.30'

    Returns:
        str: File name safe name, e.g. 'Saint_Louis', None if nothing usable is left.
    """
    if not raw_name or not raw_name.strip():
        return None
    # Remove everything from "-L" or "–L" onward (including the -L)
    name = re.sub(r'[-–]L.*$', '', raw_name, flags=re.IGNORECASE).strip()
    if not name:
        return None
    # Normalize Unicode characters (é -> e, etc.)
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    # Keep letters and numbers only, joined by single underscores
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name or None


class IslandDockTemplateExtractor(IslandDock):
    def extract_character_templates(self, folder_path=TEMPLATE_FOLDER):
        """
        Must start in the dock selection page.

        Returns:
            dict: {'extracted': int, 'skipped': int}, None if not in the dock.
        """
        if not self.is_in_island_dock():
            logger.warning('Not in island dock, open the character selection page first')
            return None

        os.makedirs(folder_path, exist_ok=True)
        existing = {os.path.splitext(f)[0].lower() for f in os.listdir(folder_path) if f.endswith('.png')}
        logger.info(f'Found {len(existing)} existing templates')

        use_ocr = getattr(self.config, 'SERVER', '').lower() == 'en'
        logger.info(f'Server: {self.config.SERVER}, Using OCR: {"Yes" if use_ocr else "No"}')
        name_ocr = None
        if use_ocr:
            name_ocr = Ocr(
                buttons=[Button(area=NAME_DISPLAY_AREA, color=(255, 255, 255), button=NAME_DISPLAY_AREA,
                                name='CHARACTER_NAME')],
                lang='cnocr',
                letter=(255, 255, 255),
                threshold=128,
                name='SELECTED_CHARACTER_NAME',
            )
        stats = {'extracted': 0, 'skipped': 0}

        def handle_page(characters):
            # Templates are cropped from the clean page, clicking a card highlights it
            clean_image = self.device.image.copy()
            for character in characters:
                identity = character.identity
                if identity not in (None, '', 'unknown') and identity.lower() in existing:
                    stats['skipped'] += 1
                    continue

                if use_ocr:
                    self.device.click(character.button)
                    self.device.sleep(0.2)
                    self.device.screenshot()
                    name = clean_character_name(name_ocr.ocr(self.device.image))
                    # Deselect the card
                    self.device.click(ISLAND_CLICK_SAFE_AREA)
                    self.device.sleep(0.3)
                    if not name:
                        logger.warning(f'OCR could not read the name of {character.button.name}, skip it')
                        stats['skipped'] += 1
                        continue
                    logger.info(f'Cleaned name: "{name}"')
                    if name.lower() in existing:
                        logger.info(f'Skipping existing: {name}')
                        stats['skipped'] += 1
                        continue
                    filename = f'{name}.png'
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:21]
                    filename = f'UNKNOWN_{timestamp}.png'

                x1, y1 = character.button.area[:2]
                area = (x1 + TEMPLATE_AREA[0], y1 + TEMPLATE_AREA[1], x1 + TEMPLATE_AREA[2], y1 + TEMPLATE_AREA[3])
                Image.fromarray(crop(clean_image, area)).save(os.path.join(folder_path, filename))
                existing.add(filename[:-4].lower())
                stats['extracted'] += 1
                logger.info(f'Saved: {filename}')

            if use_ocr:
                # The dock search compares the page before and after dragging to find the end of the list.
                # Leave a screenshot without a highlighted card behind.
                self.device.screenshot()
            # Walk the whole dock
            return None

        # Unknown cards are what this tool looks for, so the search can't report a complete scan.
        # Every page waits for identity recognition to settle, which takes a few seconds on new cards.
        self.island_dock_search(
            handle_page, descending=True, start_at_top=True, timeout=1800,
            disabled=('emotion', 'emotion_limit', 'grade'))

        logger.info(f'Extracted {stats["extracted"]} new templates, skipped {stats["skipped"]} existing')
        logger.info(f'Templates saved to: {folder_path}')
        self.ensure_dock_page_at_top()
        return stats


if __name__ == '__main__':
    az = IslandDockTemplateExtractor('alas')
    az.device.screenshot()
    az.extract_character_templates()
