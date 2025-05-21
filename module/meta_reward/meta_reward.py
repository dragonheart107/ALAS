import module.config.server as server

from module.base.timer import Timer
from module.combat.combat import Combat
from module.logger import logger
from module.meta_reward.assets import *
from module.os_ash.assets import DOSSIER_LIST
from module.ui.assets import BACK_ARROW
from module.ui.page import page_meta_menu, page_meta_beacon, page_meta_dossier, page_meta_lab, page_meta_dos_reward, page_reward
from module.ui.ui import UI

from module.base.button import ButtonGrid
from module.base.decorator import cached_property
from module.ui.setting import Setting
from module.ui.scroll import Scroll


def _server_support_meta_upgrade():
    return server.server in ['en']

class BeaconReward(Combat, UI):
    def meta_reward_notice_appear(self):
        """
        Returns:
            bool: If appear.

        Page:
            in: page_meta_lab
        """
        if self.appear(META_REWARD_NOTICE, threshold=30):
            return True
        else:
            return False

    def meta_reward_receive(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot:

        Returns:
            bool: If received.

        Pages:
            in: page_meta_lab or REWARD_CHECK
            out: REWARD_CHECK
        """
        logger.hr('Meta reward receive', level=1)
        confirm_timer = Timer(1, count=3).start()
        received = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # End
            # REWARD_CHECK appears and REWARD_RECEIVE gets gray
            if self.appear(REWARD_CHECK, offset=(20, 20)) and \
                    self.image_color_count(REWARD_RECEIVE, color=(49, 52, 49), threshold=221, count=400):
                break

            if self.appear_then_click(REWARD_ENTER, offset=(20, 20), interval=3):
                continue
            if self.match_template_color(REWARD_RECEIVE, offset=(20, 20), interval=3):
                self.device.click(REWARD_RECEIVE)
                confirm_timer.reset()
                continue
            if self.handle_popup_confirm('META_REWARD'):
                # Lock new META ships
                confirm_timer.reset()
                continue
            if self.handle_get_items():
                received = True
                confirm_timer.reset()
                continue
            if self.handle_get_ship():
                received = True
                confirm_timer.reset()
                continue

        logger.info(f'Meta reward receive finished, received={received}')
        return received

    def meta_sync_notice_appear(self, interval=0):
        """
        "sync" is the period that you gather meta points to 100% and get a meta ship

        Returns:
            bool: If appear.

        Page:
            in: page_meta_lab
        """
        if self.appear(SYNC_REWARD_NOTICE, threshold=30, interval=interval):
            return True
        else:
            return False

    def meta_sync_receive(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot:

        Returns:
            bool: If received.

        Pages:
            in: SYNC_ENTER
            out: SYNC_ENTER if meta ship synced < 100%
                REWARD_ENTER if meta ship synced >= 100%
        """
        logger.hr('Meta sync receive', level=1)
        received = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # End
            # Sync progress >= 100%
            if self.appear(REWARD_ENTER, offset=(20, 20)):
                logger.info('meta_sync_receive ends at REWARD_ENTER')
                break
            if self.appear(SYNC_ENTER, offset=(20, 20)):
                if not self.meta_sync_notice_appear():
                    logger.info('meta_sync_receive ends at SYNC_ENTER')
                    break

            # Click
            if self.handle_popup_confirm('META_REWARD'):
                # Lock new META ships
                continue
            if self.handle_get_items():
                received = True
                continue
            if self.handle_get_ship():
                received = True
                continue
            if self.meta_sync_notice_appear(interval=3):
                logger.info(f'meta_sync_notice_appear -> {SYNC_ENTER}')
                self.device.click(SYNC_ENTER)
                received = True
                continue
            if self.appear_then_click(SYNC_TAP, offset=(20, 20), interval=3):
                received = True
                continue

        logger.info(f'Meta sync receive finished, received={received}')
        return received

    def meta_wait_reward_page(self, skip_first_screenshot=True):
        """
        Wait the circle loading animation
        """
        timeout = Timer(2, count=6).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if timeout.reached():
                logger.warning(f'meta_wait_reward_page timeout')
                break
            if self.appear(REWARD_ENTER, offset=(20, 20)):
                logger.info(f'meta_wait_reward_page ends at {REWARD_ENTER}')
                break
            if self.appear(SYNC_ENTER, offset=(20, 20)):
                logger.info(f'meta_wait_reward_page ends at {SYNC_ENTER}')
                break
            if self.appear(SYNC_TAP, offset=(20, 20)):
                logger.info(f'meta_wait_reward_page ends at {SYNC_TAP}')
                break
            if self.meta_sync_notice_appear():
                logger.info('meta_wait_reward_page ends at sync red dot')
                break
            if self.meta_reward_notice_appear():
                logger.info('meta_wait_reward_page ends at reward red dot')
                break

    def run(self):
        if self.config.SERVER in ['cn', 'en', 'jp']:
            pass
        else:
            logger.info(f'MetaReward is not supported in {self.config.SERVER}, please contact server maintainers')
            return

        self.ui_ensure(page_meta_lab)
        self.meta_wait_reward_page()

        # Sync rewards
        # "sync" is the period that you gather meta points to 100% and get a meta ship
        if self.meta_sync_notice_appear():
            logger.info('Found meta sync red dot')
            self.meta_sync_receive()
        else:
            logger.info('No meta sync red dot')

        # Meta rewards
        if self.meta_reward_notice_appear():
            logger.info('Found meta reward red dot')
            self.meta_reward_receive()
        else:
            logger.info('No meta reward red dot')

        if self.appear(REWARD_CHECK):
            logger.info(f'proceed to click reward')
            self.meta_reward_receive()
            logger.info(f'met_reward_receive done')
        else:
            logger.info(f'couldnt find reward check, trying fallback')
            self.device.click(BACK_ARROW)
            logger.info(f'click 1 page back')
            if self.appear(META_LAB_LIST):
                logger.info(f'found meta lab list')
                if self.meta_sync_notice_appear():
                    logger.info('Found meta sync red dot')
                    self.meta_sync_receive()
                else:
                    logger.info('No meta sync red dot')

                if self.meta_reward_notice_appear():
                    logger.info(f'found reward notice from lab list')
                    self.meta_reward_receive()
                    logger.info('tried meta reward receive again')

class DossierReward(Combat, UI):
    def meta_reward_notice_appear(self):
        """
        Returns:
            bool: If appear.

        Page:
            in: dossier meta page
        """
        self.device.screenshot()
        if self.appear(DOSSIER_REWARD_RECEIVE, offset=(-40, 10, -10, 40), similarity=0.7):
            logger.info('Found dossier reward red dot')
            return True
        else:
            logger.info('No dossier reward red dot')
            return False

    def meta_reward_enter(self, skip_first_screenshot=True):
        """
        Pages:
            in: dossier meta page
            out: DOSSIER_REWARD_CHECK
        """
        logger.info('Dossier reward enter')
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(DOSSIER_LIST, offset=(20, 20)):
                self.device.click(DOSSIER_REWARD_ENTER)
                continue

            # End
            if self.appear(DOSSIER_REWARD_CHECK, offset=(20, 20)):
                break

    def meta_reward_receive(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot:

        Returns:
            bool: If received.

        Pages:
            in: DOSSIER_REWARD_CHECK
            out: DOSSIER_REWARD_CHECK
        """
        logger.hr('Dossier reward receive', level=1)
        confirm_timer = Timer(1, count=3).start()
        received = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.match_template_color(DOSSIER_REWARD_RECEIVE, offset=(20, 20), interval=3):
                self.device.click(DOSSIER_REWARD_RECEIVE)
                confirm_timer.reset()
                continue
            if self.handle_popup_confirm('DOSSIER_REWARD'):
                # Lock new META ships
                confirm_timer.reset()
                continue
            if self.handle_get_items():
                received = True
                confirm_timer.reset()
                continue
            if self.handle_get_ship():
                received = True
                confirm_timer.reset()
                continue

            # End
            if not self.appear(DOSSIER_REWARD_RECEIVE, offset=(20, 20)):
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()

        logger.info(f'Dossier reward receive finished, received={received}')
        return received

    def run(self):
        if self.config.SERVER in ['cn', 'en', 'jp']:
            pass
        else:
            logger.info(f'MetaReward is not supported in {self.config.SERVER}, please contact server maintainers')
            return
        self.ui_ensure(page_meta_dossier)
        if self.meta_reward_notice_appear():
            self.meta_reward_enter()
            self.meta_reward_receive()


class MetaReward(BeaconReward, DossierReward):
    def run(self, category="beacon"):
        if category == "beacon":
            BeaconReward(self.config, self.device).run()
        elif category == "dossier":
            DossierReward(self.config, self.device).run()
        else:
            logger.info(f'Possible wrong parameter {category}, please contact the developers.')

#LAB_SCROLL = Scroll(LAB_SCROLL,color= name='LAB_SCROLL') color error, replace with simple swipe?

SHIP_GRIDS_SELECT = ButtonGrid(
    origin=(8, 405), delta=(0, 75), button_shape=(226, 69), grid_shape=(1, 1), name='META_LAB_SHIPS') #select first landing page 1st

SHIP_GRIDS = ButtonGrid(
    origin=(8, 480), delta=(0, 47), button_shape=(133, 41), grid_shape=(1, 4), name='META_LAB_SHIPS') #non select landing page 2nd

class MetaLabFilter(Button, UI):
    def handle_dock_cards_loading(self):
        # Poor implementation.
        self.device.sleep((1, 1.5))
        self.device.screenshot()    

    def dock_filter_enter(self):
        self.ui_click(LAB_FILTER, appear_button=LAB_LIST_CHECK, check_button=LAB_FILTER_CONFIRM,
                      skip_first_screenshot=True)

    def dock_filter_confirm(self, wait_loading=True):
        """
        Args:
            wait_loading: Default to True, use False on continuous operation
        """
        self.ui_click(LAB_FILTER_CONFIRM, check_button=LAB_LIST_CHECK, skip_first_screenshot=True)
        if wait_loading:
            self.handle_dock_cards_loading()

    @cached_property
    def dock_filter(self) -> Setting:
        delta = (147 + 1 / 3, 57)
        button_shape = (139, 42)
        setting = Setting(name='METALAB', main=self)
        setting.add_setting(
            setting='type',
            option_buttons=ButtonGrid(
                origin=(219, 213), delta=delta, button_shape=button_shape, grid_shape=(7, 2), name='FILTER_TYPE'),
            option_names=['all', 'vanguard', 'main', 'dd', 'cl', 'ca', 'bb', 'cv', 'ar', 'ss', 'others', 'not_available', 'not_available', 'not_available'],
            option_default='all'
        )
        setting.add_setting(
            setting='rarity',
            option_buttons=ButtonGrid(
                origin=(219, 343), delta=delta, button_shape=button_shape, grid_shape=(7, 1), name='FILTER_RARITY'),
            option_names=['all', 'elite', 'super_rare', 'not_available', 'not_available', 'not_available', 'not_available'],
            option_default='all'
        )
        setting.add_setting(
            setting='extra',
            option_buttons=ButtonGrid(
                origin=(219, 416), delta=delta, button_shape=button_shape, grid_shape=(7, 1), name='FILTER_EXTRA'),
            option_names=['no_limit', 'enhanceable', 'can_level_skill', 'can_limit_break', 'not_available', 'not_available', 'not_available'],
            option_default='no_limit'
        )
        return setting

    def dock_filter_set(
            self,
            type='all',
            rarity='all',
            extra='no_limit',
            wait_loading=True
    ):
        """
        A faster filter set function.

        Args:
            type (str, list):
                ['all', 'vanguard', 'main', 'dd', 'cl', 'ca', 'bb', 'cv', 'ar', 'ss', 'others', 'not_available', 'not_available', 'not_available']
            rarity (str, list):
                ['all', 'elite', 'super_rare', 'not_available', 'not_available', 'not_available''not_available']
            extra (str, list):
                ['no_limit', 'enhanceable', 'can_level_skill', 'can_limit_break', 'not_available', 'not_available', 'not_available']

        Pages:
            in: page_dock
        """
        self.dock_filter_enter()
        self.dock_filter.set(type=type, rarity=rarity, extra=extra)
        self.dock_filter_confirm(wait_loading=wait_loading)

class MetaEnhance(MetaLabFilter):
    def meta_enhance(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear_then_click(META_MAT):
                continue
            if self.appear(META_NOMAT):
                break

    def meta_enhance_select(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            self.wait_until_stable(META_REL)
            if not self.appear(META_FP_LOCK) and self.appear_then_click(META_FP):
                self.meta_enhance()
                continue
            if not self.appear(META_TORP_LOCK) and self.appear_then_click(META_TORP):
                self.meta_enhance()
                continue
            if not self.appear(META_AVI_LOCK) and self.appear_then_click(META_AVI):
                self.meta_enhance()
                continue
            if self.appear_then_click(META_REL):
                self.meta_enhance()
                break

    
    def meta_limit_enhance():
        'do sth'
        

    def meta_skill_select():
        'do sth'

    def run(self):
        if self.config.SERVER in ['en']:
            pass
        else:
            logger.info(f'MetaReward is not supported in {self.config.SERVER}, please contact server maintainers')
            return
        self.ui_ensure(page_meta_lab)
            #self.config.OpsiAshBeacon_
        if not self.appear(LAB_LIST_CHECK):
            self.device.click(BACK_ARROW)
        while 1:
            self.dock_filter_set(extra='enhanceable')
            if self.appear_then_click(META_ENHANCE):
                while 1:
                    self.meta_enhance_select()
            self.dock_filter_set(extra='can_level_skill')
            if self.appear_then_click(META_SKILL):
                while 1:
                    self.meta_skill_select()
            self.dock_filter_set(extra='can_limit_break')
            if self.appear_then_click(META_LIMIT):
                while 1:
                    self.meta_limit_enhance()
#meta rel appears last wait fpor stabel
