from src.common import config, settings, utils
import time
from src.routine.components import Command, CustomKey, SkillCombination, Fall, BaseSkill, GoToMap, ChangeChannel, Frenzy
from src.common.vkeys import press, key_down, key_up
import cv2

IMAGE_DIR = config.RESOURCES_DIR + '/command_books/night_lord/'

frame = config.capture.frame
#height, width, _ = frame.shape
#item_frame = frame[height//2-100:height//2+200, width //2-150:width//2+150]
DEATH_DEBUFF_TEMPLATE = cv2.imread(IMAGE_DIR + 'dp_template.png', 0)
CHARM_TEMPLATE = cv2.imread(IMAGE_DIR + 'charm_template.png', 0)
CASH_TAB_TEMPLATE = cv2.imread(IMAGE_DIR + 'cashtab_template.png', 0)


ASSASSIN_MARK_TEMPLATE = cv2.imread(IMAGE_DIR + 'AssassinMark.png', 0)

# List of key mappings
class Key:
    # Movement
    JUMP = 'alt'
    FLASH_JUMP = 'alt'
    ROPE = '`'
    UP_JUMP = 'c'

    # Buffs
    SKILL_AM = '\\' #Assassin Mark
    SKILL_6 = '6' #Maple Warrior
    
    # Potions
    SKILL_0 = '0' #Elite Box
    SKILL_7 = '7' #WAP potion
    SKILL_8 = '8' #MP potion

    # Attack Skills
    SKILL_A = 'a' # 挑釁契約
    SKILL_1 = '1' # 達克魯的秘傳
    SKILL_D = 'd' # 絕殺領域
    SKILL_S = 's'# 風魔手裏劍
    SKILL_W = 'w' # 穢土轉生
    SKILL_E = 'e' # 四星鏢雨
    SKILL_R = 'r' # 6th job Origin skill 
    SKILL_4 = '4' # 飛閃起爆符
    SKILL_F = 'f' # 
    SKILL_F2 = 'f2' # 
    SKILL_2 = '2' # Spider
    SKILL_3 = '3' # 
    SKILL_5 = 'down+5' # 噴泉 fountain
    # special Skills
    SP_F12 = 'f12' # 輪迴

def step(direction, target):
    """
    Performs one movement step in the given DIRECTION towards TARGET.
    Should not press any arrow keys, as those are handled by Auto Maple.
    """

    d_y = target[1] - config.player_pos[1]
    d_x = target[0] - config.player_pos[0]

    if direction == 'left' or direction == 'right':
        if abs(d_x) >= 18:
            if abs(d_x) >= 60:
                FlashJump(direction='',triple_jump='true',fast_jump='false').execute()
                SkillCombination(direction='',jump='false',target_skills='skill_a').execute()
            elif abs(d_x) >= 23:
                FlashJump(direction='',triple_jump='false',fast_jump='false').execute()
                SkillCombination(direction='',jump='false',target_skills='skill_a').execute()
            else:
                SkillCombination(direction='',jump='true',target_skills='skill_a').execute()
            time.sleep(utils.rand_float(0.05, 0.07))
            if abs(d_x) <= 22:
                key_up(direction)
            if config.player_states['movement_state'] == config.MOVEMENT_STATE_FALLING:
                SkillCombination(direction='',jump='false',target_skills='skill_a').execute()
            utils.wait_for_is_standing(200)
        else:
            time.sleep(utils.rand_float(0.08, 0.12))
            utils.wait_for_is_standing(200)
    
    if direction == 'up':
        utils.wait_for_is_standing(500)
        if abs(d_y) > 6 :
            if abs(d_y) > 36:
                press(Key.JUMP, 1)
                time.sleep(utils.rand_float(0.1, 0.15))
                press(Key.ROPE, 1)
                time.sleep(utils.rand_float(1.2, 1.5))
            elif abs(d_y) < 15:
                UpJump().execute()
                SkillCombination(direction='',jump='false',target_skills='skill_a|skill_1').execute()
            else:
                press(Key.ROPE, 1)
                time.sleep(utils.rand_float(1.2, 1.5))
            utils.wait_for_is_standing(300)
        else:
            press(Key.JUMP, 1)
            time.sleep(utils.rand_float(0.1, 0.15))

    if direction == 'down':
        down_duration = 0.04
        if abs(d_y) > 20:
            down_duration = 0.14
        elif abs(d_y) > 13:
            down_duration = 0.1
        
        if config.player_states['movement_state'] == config.MOVEMENT_STATE_STANDING and config.player_states['in_bottom_platform'] == False:
            print("down stair")
            if abs(d_x) >= 2:
                if d_x > 0:
                    Fall(direction='right',duration=down_duration).execute()
                else:
                    Fall(direction='left',duration=down_duration).execute()
            else:
                Fall(direction='',duration=down_duration).execute()
            SkillCombination(direction='',jump='false',target_skills='skill_a').execute()
        time.sleep(utils.rand_float(0.02, 0.05))
        utils.wait_for_is_standing(300)

class Adjust(Command):
    """Fine-tunes player position using small movements."""

    def __init__(self, x, y, max_steps=5):
        super().__init__(locals())
        self.target = (float(x), float(y))
        self.max_steps = settings.validate_nonnegative_int(max_steps)

    def main(self):
        counter = self.max_steps
        toggle = True
        threshold = settings.adjust_tolerance
        d_x = self.target[0] - config.player_pos[0]
        d_y = self.target[1] - config.player_pos[1]
        while config.enabled and counter > 0 and (abs(d_x) > threshold or abs(d_y) > threshold):
            if toggle:
                d_x = self.target[0] - config.player_pos[0]
                if abs(d_x) > threshold:
                    walk_counter = 0
                    if d_x < 0:
                        key_down('left')
                        while config.enabled and d_x < -1 * threshold and walk_counter < 60:
                            time.sleep(utils.rand_float(0.01, 0.02))
                            walk_counter += 1
                            d_x = self.target[0] - config.player_pos[0]
                        key_up('left')
                    else:
                        key_down('right')
                        while config.enabled and d_x > threshold and walk_counter < 60:
                            time.sleep(utils.rand_float(0.01, 0.02))
                            walk_counter += 1
                            d_x = self.target[0] - config.player_pos[0]
                        key_up('right')
                    counter -= 1
            else:
                d_y = self.target[1] - config.player_pos[1]
                if abs(d_y) > settings.adjust_tolerance:
                    if d_y < 0:
                        utils.wait_for_is_standing(1000)
                        UpJump('up').main()
                    else:
                        utils.wait_for_is_standing(1000)
                        key_down('down')
                        time.sleep(utils.rand_float(0.05, 0.07))
                        press(Key.JUMP, 2, down_time=0.1)
                        key_up('down')
                        time.sleep(utils.rand_float(0.17, 0.25))
                    counter -= 1
            d_x = self.target[0] - config.player_pos[0]
            d_y = self.target[1] - config.player_pos[1]
            toggle = not toggle

class Buff(Command):
    """Uses each of Adele's buffs once."""

    def __init__(self):
        super().__init__(locals())
        self.cd120_buff_time = 0
        self.cd150_buff_time = 0
        self.cd180_buff_time = 0
        self.cd200_buff_time = 0
        self.cd240_buff_time = 0
        self.cd900_buff_time = 0
        self.decent_buff_time = 0

    def main(self):
        # buffs = [Key.SPEED_INFUSION, Key.HOLY_SYMBOL, Key.SHARP_EYE, Key.COMBAT_ORDERS, Key.ADVANCED_BLESSING]
        now = time.time()
        utils.wait_for_is_standing(1000)
        if self.cd120_buff_time == 0 or now - self.cd120_buff_time > 121:
            self.cd120_buff_time = now
        if self.cd180_buff_time == 0 or now - self.cd150_buff_time > 151:
            self.cd150_buff_time = now
        if self.cd180_buff_time == 0 or now - self.cd180_buff_time > 181:
            Skill_4().execute()
            self.cd180_buff_time = now
        if self.cd200_buff_time == 0 or now - self.cd200_buff_time > 200:
            self.cd200_buff_time = now
        if self.cd240_buff_time == 0 or now - self.cd240_buff_time > 240:
            self.cd240_buff_time = now
        if self.cd900_buff_time == 0 or now - self.cd900_buff_time > 900:
            self.cd900_buff_time = now
        # if self.decent_buff_time == 0 or now - self.decent_buff_time > settings.buff_cooldown:
        #     for key in buffs:
        #       press(key, 3, up_time=0.3)
        #       self.decent_buff_time = now	

class FlashJump(Command):
    """Performs a flash jump in the given direction."""
    _display_name = '二段跳'

    def __init__(self, direction="",jump='false',combo='False',triple_jump="False",fast_jump="false"):
        super().__init__(locals())
        self.direction = settings.validate_arrows(direction)
        self.triple_jump = settings.validate_boolean(triple_jump)
        self.fast_jump = settings.validate_boolean(fast_jump)
        self.jump = settings.validate_boolean(jump)

    def main(self):
        if not self.jump:
            self.player_jump(self.direction)
        else:
            key_down(self.direction,down_time=0.05)
            press(Key.JUMP,down_time=0.04,up_time=0.02)
        if not self.fast_jump:
            time.sleep(utils.rand_float(0.02, 0.04)) # fast flash jump gap
        else:
            time.sleep(utils.rand_float(0.2, 0.25)) # slow flash jump gap
        if self.direction == 'up':
            press(Key.FLASH_JUMP, 1)
        else:
            press(Key.FLASH_JUMP, 1,down_time=0.06,up_time=0.05)
            if self.triple_jump:
                time.sleep(utils.rand_float(0.05, 0.08))
                press(Key.FLASH_JUMP, 1,down_time=0.07,up_time=0.04) # if this job can do triple jump
        key_up(self.direction,up_time=0.01)
        time.sleep(utils.rand_float(0.02, 0.04))

class CheckDeathPenalty(Command):
    _display_name ='Check Death Penalty'

    def main(self):
        frame = config.capture.frame

        # check for debuff
        death_debuff = utils.multi_match(frame[:95, :], DEATH_DEBUFF_TEMPLATE,threshold=0.93)
        
        if len(death_debuff) > 0 :

            #Open inventory
            press("i")

            #capture frame with invent opened
            frame = config.capture.frame

            #Check if cash tab is cuurently selected
            cash_tab_icon = utils.multi_match(frame[:, :], CASH_TAB_TEMPLATE,threshold = 0.93)
            if len(cash_tab_icon) > 0 :
                cash_tab_pos = min(cash_tab_icon, key=lambda p: p[0])
                target = (round(cash_tab_pos[0]), round(cash_tab_pos[1]))
                utils.game_window_click(target, button='left', click_time = 1, delay = 0.01)

            #ADJUST this if u get a noti saying you are in combat and you cant use item
            time.sleep(0.2)

            #Recapture a new frame with charm in the picture
            frame = config.capture.frame

            #Check for safety charm
            charm_icon = utils.multi_match(frame[:, :], CHARM_TEMPLATE,threshold = 0.93)

            #Use charm
            if len(charm_icon) > 0 :
                charm_pos = min(charm_icon, key=lambda p: p[0])
                print('charm_pos : ', charm_pos)
                target = (round(charm_pos[0]), round(charm_pos[1]))
                utils.game_window_click(target, button='left', click_time = 2, delay = 0.01)
            else:
                print("No charm in inventory!")

            #Close inventory
            press("i")

        else:
            #No death debuff effects
            print("no debuff effect")
            
                
            

class CheckAssassinMark(Command):
    _display_name ='Check AssassinMark'

    def main(self):
        frame = config.capture.frame
        # check in rune buff
        am_buff = utils.multi_match(frame[:95, :], ASSASSIN_MARK_TEMPLATE,threshold=0.9)
        if len(am_buff) > 0 :
            print("in buff")
        else:
            print("out buff")
            Skill_AM().execute()            

class FaceLeft(BaseSkill):
    """Performs a flash jump in the given direction."""
    _display_name = 'FaceLeft'
    _distance = 1
    key='left'
    delay=0.1
    rep_interval=0
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.0

class FaceRight(BaseSkill):
    """Performs a flash jump in the given direction."""
    _display_name = 'FaceRight'
    _distance = 1
    key='right'
    delay=0.1
    rep_interval=0
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.0

class PressUp(BaseSkill):
    """Performs a flash jump in the given direction."""
    _display_name = 'PressUp'
    _distance = 1
    key='up'
    delay=0.25
    rep_interval=0
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.0

class FJSD(Command):
    """Performs a flash jump in the given direction."""
    _display_name = 'FJSD'

    def main(self):
        press(Key.JUMP,down_time=0.04,up_time=0.02)
        press(Key.FLASH_JUMP, 1,down_time=0.06,up_time=0.05)
        press(Key.SKILL_A, 2)
        time.sleep(0.3)

class UpJump(BaseSkill):
    """Performs a up jump in the given direction."""
    _display_name = '上跳'
    _distance = 27
    key=Key.UP_JUMP
    delay=0.4
    rep_interval=0.5
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.4

    # def __init__(self,jump='false', direction='',combo='true'):
    #     super().__init__(locals())
    #     self.direction = settings.validate_arrows(direction)

    # def main(self):
    #     utils.wait_for_is_standing(500)
    #     press(Key.UP_JUMP, 1)
    #     key_down(self.direction)
    #     time.sleep(utils.rand_float(0.35, 0.4))
    #     if 'left' in self.direction or 'right' in self.direction:
    #         press(Key.JUMP, 1)
    #     key_up(self.direction)
        
class Rope(BaseSkill):
    """Performs a up jump in the given direction."""
    _display_name = '連接繩索'
    _distance = 27
    key=Key.ROPE
    delay=1.4
    rep_interval=0.5
    skill_cool_down=3
    ground_skill=False
    buff_time=0
    combo_delay = 0.2

class Skill_AM(BaseSkill):
    _display_name = 'Assassin Mark'
    _distance = 27
    key=Key.SKILL_AM
    delay=0.5
    rep_interval=0.5
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.5

class Skill_0(BaseSkill):
    _display_name = 'Elite Box'
    _distance = 27
    key=Key.SKILL_0
    delay=0.5
    rep_interval=0.5
    skill_cool_down= 60
    ground_skill=False
    buff_time=0
    combo_delay = 0.5

class Skill_A(BaseSkill):
    _display_name = '挑釁契約'
    _distance = 27
    key=Key.SKILL_A
    delay=0.5
    rep_interval=0.5
    skill_cool_down=0
    ground_skill=False
    buff_time=0
    combo_delay = 0.5

class Skill_1(BaseSkill):
    _display_name = '達克魯的秘傳'
    _distance = 27
    key=Key.SKILL_1
    delay=0.45
    rep_interval=0.5
    skill_cool_down=57
    ground_skill=True
    buff_time=12
    combo_delay = 0.5

class Skill_D(BaseSkill):
    _display_name = '絕殺領域'
    _distance = 27
    key=Key.SKILL_D
    delay=0.45
    rep_interval=0.5
    skill_cool_down=57
    ground_skill=True
    buff_time=60
    combo_delay = 0.5

class Skill_S(BaseSkill):
    _display_name = '風魔手裏劍'
    _distance = 50
    key=Key.SKILL_S
    delay=0.45
    rep_interval=0.5
    skill_cool_down=24
    ground_skill=False
    buff_time=0
    combo_delay = 0.45

class Skill_W(BaseSkill):
    _display_name = '穢土轉生'
    _distance = 50
    key=Key.SKILL_W
    delay=0.63
    rep_interval=0.5
    skill_cool_down=29
    ground_skill=False
    buff_time=0
    combo_delay = 0.63

class Skill_R(BaseSkill):
    _display_name = '6th Job-Origin Skill'
    _distance = 50
    key=Key.SKILL_R
    delay=0.63
    rep_interval=0.5
    skill_cool_down=360
    ground_skill=False
    buff_time=0
    combo_delay = 0.63

class Skill_E(BaseSkill):
    _display_name = '四星鏢雨'
    _distance = 50
    key=Key.SKILL_E
    delay=0.68
    rep_interval=0.5
    skill_cool_down=14
    ground_skill=False
    buff_time=0
    combo_delay = 0.68

class Skill_2(BaseSkill):
    _display_name ='蜘蛛之鏡'
    key=Key.SKILL_2
    delay=0.7
    rep_interval=0.25
    skill_cool_down=240
    ground_skill=False
    buff_time=0
    combo_delay = 0.4

class Skill_4(BaseSkill):
    _display_name ='飛閃起爆符'
    key=Key.SKILL_4
    delay=0.7
    rep_interval=0.25
    skill_cool_down=180
    ground_skill=True
    buff_time=90
    combo_delay = 0.4

class Skill_7(BaseSkill):
    _display_name ='WAP Potion'
    key=Key.SKILL_7
    delay=0.7
    rep_interval=0.25
    skill_cool_down=7230
    ground_skill=False
    buff_time=7225
    combo_delay = 0.4

class Skill_8(BaseSkill):
    _display_name ='MonsterPark'
    key=Key.SKILL_8
    delay=0.7
    rep_interval=0.25
    skill_cool_down=1800
    ground_skill=False
    buff_time=1799
    combo_delay = 0.4

class Skill_6(BaseSkill):
    _display_name ='Maple Warrior'
    key=Key.SKILL_6
    delay=0.7
    rep_interval=0.25
    skill_cool_down=850
    ground_skill=False
    buff_time=900
    combo_delay = 0.4

class Skill_5(BaseSkill):
    _display_name ='噴泉'
    key=Key.SKILL_5
    delay=0.9
    rep_interval=0.25
    skill_cool_down=57
    ground_skill=True
    buff_time=60
    combo_delay = 0.3

class AutoHunting(Command):
    _display_name ='自動走位狩獵'

    def __init__(self,duration='180',map=''):
        super().__init__(locals())
        self.duration = float(duration)
        self.map = map

    def main(self):
        daily_complete_template = cv2.imread('assets/daily_complete.png', 0)
        start_time = time.time()
        toggle = True
        move = config.bot.command_book['move']
        GoToMap(target_map=self.map).execute()
        SkillCombination(direction='',target_skills='skill_a').execute()
        minimap = config.capture.minimap['minimap']
        height, width, _n = minimap.shape
        bottom_y = height - 30
        # bottom_y = config.player_pos[1]
        settings.platforms = 'b' + str(int(bottom_y))
        while True:
            if settings.auto_change_channel and config.should_solve_rune:
                Skill_A().execute()
                config.bot._solve_rune()
                continue
            if settings.auto_change_channel and config.should_change_channel:
                ChangeChannel(max_rand=40).execute()
                Skill_A().execute()
                continue
            Frenzy().execute()
            frame = config.capture.frame
            point = utils.single_match_with_threshold(frame,daily_complete_template,0.9)
            if len(point) > 0:
                print("one daily end")
                break
            minimap = config.capture.minimap['minimap']
            height, width, _n = minimap.shape
            if time.time() - start_time >= self.duration:
                break
            if not config.enabled:
                break
            
            if toggle:
                # right side
                move((width-20),bottom_y).execute()
                if config.player_pos[1] >= bottom_y:
                    print('new bottom')
                    bottom_y = config.player_pos[1]
                    settings.platforms = 'b' + str(int(bottom_y))
                print("current bottom : ", settings.platforms)
                print("current player : ", str(config.player_pos[1]))
                FlashJump(direction='left').execute()
                Rope(rep='2',combo='True').execute()
                SkillCombination(direction='left',target_skills='skill_w|skill_s|skill_e|skill_a').execute()
            else:
                # left side
                move(20,bottom_y).execute()
                if config.player_pos[1] >= bottom_y:
                    print('new bottom')
                    bottom_y = config.player_pos[1]
                    settings.platforms = 'b' + str(int(bottom_y))
                print("current bottom : ", settings.platforms)
                FlashJump(direction='right').execute()
                Rope(rep='2',combo='True').execute()
                SkillCombination(direction='right',target_skills='skill_w|skill_s|skill_e|skill_a').execute()
            
            if settings.auto_change_channel and config.should_solve_rune:
                config.bot._solve_rune()
                continue
            if settings.auto_change_channel and config.should_change_channel:
                ChangeChannel(max_rand=40).execute()
                Skill_A().execute()
                continue
            move(width//2,bottom_y).execute()
            UpJump(jump='true').execute()
            SkillCombination(direction='left',target_skills='skill_w|skill_s|skill_e|skill_a').execute()
            SkillCombination(direction='right',target_skills='skill_1|skill_d|skill_a').execute()
            toggle = not toggle
            

        if settings.home_scroll_key:
            config.map_changing = True
            press(settings.home_scroll_key)
            time.sleep(5)
            config.map_changing = False
        return
