"""A module for tracking useful in-game information."""

import time
import cv2
import threading
import ctypes
import mss
import mss.windows
import numpy as np
from src.common import config, utils, settings
from ctypes import wintypes
from ctypes import windll, byref, c_ubyte
from ctypes.wintypes import RECT, HWND, BOOL, HDC, UINT
import win32gui
import win32con
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()



# The distance between the top of the minimap and the top of the screen
MINIMAP_TOP_BORDER = 5

# The thickness of the other three borders of the minimap
MINIMAP_BOTTOM_BORDER = 6

# Offset in pixels to adjust for windowed mode
WINDOWED_OFFSET_TOP = 36
WINDOWED_OFFSET_LEFT = 10

# The top-left and bottom-right corners of the minimap
MM_TL_TEMPLATE = cv2.imread('assets/minimap_tl_template.png', 0)
MM_BR_TEMPLATE = cv2.imread('assets/minimap_br_template.png', 0)

MMT_HEIGHT = max(MM_TL_TEMPLATE.shape[0], MM_BR_TEMPLATE.shape[0])
# print('\n Minimap height:', MMT_HEIGHT)
MMT_WIDTH = max(MM_TL_TEMPLATE.shape[1], MM_BR_TEMPLATE.shape[1])
# print('\n Minimap width:', MMT_WIDTH)

# The player's symbol on the minimap
PLAYER_TEMPLATE = cv2.imread('assets/player_template.png', 0)
PT_HEIGHT, PT_WIDTH = PLAYER_TEMPLATE.shape
print('\n Player height:', PT_HEIGHT)
print('\n Player width:', PT_WIDTH)

GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
CreateCompatibleDC = windll.gdi32.CreateCompatibleDC
CreateCompatibleBitmap = windll.gdi32.CreateCompatibleBitmap
SelectObject = windll.gdi32.SelectObject
BitBlt = windll.gdi32.BitBlt
DeleteObject = windll.gdi32.DeleteObject
GetBitmapBits = windll.gdi32.GetBitmapBits
GetClientRect = windll.user32.GetClientRect
PrintWindow = windll.user32.PrintWindow
ClientToScreen = windll.user32.ClientToScreen
PrintWindow.restype = BOOL
PrintWindow.argtypes = (HWND, HDC, UINT)

PW_RENDERFULLCONTENT = 0x00000002
CAPTUREBLT = 0x40000000
SRCCOPY = 0x00CC0020

class Capture:
    """
    A class that tracks player position and various in-game events. It constantly updates
    the config module with information regarding these events. It also annotates and
    displays the minimap in a pop-up window.
    """

    def __init__(self):
        """Initializes this Capture object's main thread."""

        config.capture = self
        self.capture_gap_sec = 0.015
        self.frame = None
        self.minimap = None
        self.minimap_ratio = 1
        self.minimap_sample = None
        self.sct = None
        self.window = {
            'left': 0,
            'top': 0,
            'width': 1366, # 1366*768 is the default resolution in dev
            'height': 768,
            # 'width': 400, #only need small area at top left
            # 'height': 200,
        }
        self.default_window_resolution = {
            '1366':(1366,768),
            '1280':(1280,720)
        }
        self.latest_positions = []
        self.MAX_LATEST_POSITION_AMOUNT = 10
        self.recording_frames = []
        self.MAX_RECORDING_AMOUNT = 60
        self.ready = False
        self.calibrated = False
        self.refresh_counting = 0
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.handle = user32.FindWindowW(None, "MapleStory")
        self.check_is_standing_count = 0
        
    def start(self):
        """Starts this Capture's thread."""

        print('\n[~] Started video capture')
        self.thread.start()
    
    def auto_detect_minimap_box(self, frame_gray: np.ndarray) -> tuple:
        """
        Automatically detects the minimap's top-left and bottom-right corners using template matching.
        """
        res_tl = cv2.matchTemplate(frame_gray, MM_TL_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc_tl = cv2.minMaxLoc(res_tl)
        
        res_br = cv2.matchTemplate(frame_gray, MM_BR_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc_br = cv2.minMaxLoc(res_br)

        x1, y1 = max_loc_tl
        x2, y2 = max_loc_br

        padding_br = 8
        padding_tl = 8

        mm_tl = (
            x1 + MM_TL_TEMPLATE.shape[1] - padding_tl,
            y1 + MM_TL_TEMPLATE.shape[0]
        )

        mm_br = (
            x2 + padding_br,
            y2
        )
        return mm_tl, mm_br

    def _main(self):
        """Constantly monitors the player's position and in-game events."""

        mss.windows.CAPTUREBLT = 0
        while True:
            # Calibrate screen capture
            self.handle = user32.FindWindowW(None, "MapleStory")

            win32gui.RedrawWindow(
                self.handle,
                None,
                None,
                win32con.RDW_INVALIDATE | win32con.RDW_UPDATENOW | win32con.RDW_ALLCHILDREN
            )

            # Force bring to foreground and restore from minimized
            # if win32gui.IsIconic(self.handle):
            #     win32gui.ShowWindow(self.handle, 9)  # SW_RESTORE
            # win32gui.SetForegroundWindow(self.handle)
            
            # old version for front screenshot
            rect = wintypes.RECT()
            user32.GetWindowRect(self.handle, ctypes.pointer(rect))
            rect = (rect.left, rect.top, rect.right, rect.bottom)
            rect = tuple(max(0, x) for x in rect)
            
            if settings.full_screen:
                self.window['left'] = 0
                self.window['top'] = 0
                self.window['width'] = self.default_window_resolution['1366'][0]
                self.window['height'] = self.default_window_resolution['1366'][1]
            else:
                self.window['left'] = rect[0]
                self.window['top'] = rect[1]
                self.window['width'] = max(rect[2] - rect[0], MMT_WIDTH)
                # print('\n Minimap width:', self.window['width'])
                self.window['height'] = max(rect[3] - rect[1], MMT_HEIGHT)
                # print('\n Minimap height:', self.window['height'])

            # move game to foreground
            # win32gui.SetForegroundWindow(self.handle)
            # win32gui.MoveWindow(self.handle,0,0,self.window['width'],self.window['height'],True)

            if abs(self.default_window_resolution['1366'][0] - self.window['width']) < \
                    abs(self.default_window_resolution['1280'][0] - self.window['width']):
                # self.window['left'] = rect[0] + (self.default_window_resolution['1366'][0] - self.window['width'])
                self.window['top'] = rect[1] + abs(self.default_window_resolution['1366'][1] - self.window['height'])
                self.window['width'] = self.default_window_resolution['1366'][0]
                self.window['height'] = self.default_window_resolution['1366'][1]
            else:
                # self.window['left'] = rect[0] + (self.default_window_resolution['1280'][0] - self.window['width'])
                self.window['top'] = rect[1] + abs(self.default_window_resolution['1280'][1] - self.window['height'])
                self.window['width'] = self.default_window_resolution['1280'][0]
                self.window['height'] = self.default_window_resolution['1280'][1]

            # Calibrate by finding the bottom right corner of the minimap
            self.frame = self.screenshot_in_bg(self.handle,0,0,self.window['width'],self.window['height'])
            if self.frame is None:
                continue
            # else:
            #     cv2.imwrite("debug_initial_frame.png", self.frame)
            # tl, _ = utils.single_match(self.frame, MM_TL_TEMPLATE)
            # _, br = utils.single_match(self.frame, MM_BR_TEMPLATE)
            # 
            
            gray_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            mm_tl, mm_br = self.auto_detect_minimap_box(gray_frame)
            # DEBUG: sanity-check minimap crop
            test_crop = self.frame[mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0]]
            # cv2.imwrite("debug_minimap_region.png", test_crop)
            self.minimap_ratio = (mm_br[0] - mm_tl[0]) / (mm_br[1] - mm_tl[1])
            self.minimap_sample = self.frame[mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0]]
            cv2.rectangle(self.frame, mm_tl, mm_br, (0,255,0), 1)
            # cv2.imwrite("minimap_debug_boxed.png", self.frame)
            # cv2.imwrite("minimap_debug.png", self.frame[mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0]])
            self.calibrated = True
            self.check_is_standing_count = 0

            while True:
                if not self.calibrated:
                    self.refresh_counting = 0
                    break
                # refresh whole game frame every 0.5s
                if self.refresh_counting % 3 == 0:
                    self.frame = self.screenshot_in_bg(self.handle,0,0,self.window['width'],self.window['height'])
                    # if self.refresh_counting % 20 == 0:
                    #     cv2.imwrite('./test.png',self.frame)

                # save pic every 1s, max 60 pic
                if self.refresh_counting % 80 == 0 and config.enabled:
                    self.recording_frames.append(self.frame)
                    if len(self.recording_frames) > self.MAX_RECORDING_AMOUNT:
                        self.recording_frames.pop(0)
                elif not config.enabled and len(self.recording_frames) > 0:
                    for index in range(len(self.recording_frames)):
                        cv2.imwrite('./recording/r_' + str(index) + '.png',self.recording_frames[index])
                    self.recording_frames = []
                    
                # Take screenshot
                minimap = self.screenshot_in_bg(self.handle,mm_tl[0],mm_tl[1],mm_br[0]-mm_tl[0],mm_br[1]-mm_tl[1])
                if minimap is None:
                    continue
                
                # Determine the player's position
                player = utils.multi_match(minimap, PLAYER_TEMPLATE, threshold=0.8)

                # DEBUG: visualize all full-template matches
                # debug_minimap = minimap.copy()
                # for pt in player:
                #     cv2.circle(debug_minimap, pt, 3, (0, 255, 0), -1)  # Green dot = full match
                # print(f"[DEBUG] Matches found (full template): {len(player)}")
                
                # find left half or right half if didnt find complete player_template
                find_left_half = False
                find_right_half = False
                find_bottom_half = False
                if not player:
                    p_height, p_width = PLAYER_TEMPLATE.shape
                    left_half_player = PLAYER_TEMPLATE[0:p_height, 0 : p_width //2]
                    player = utils.multi_match(minimap, left_half_player, threshold=0.8)
                    if player:
                        find_left_half = True
                        # print(f"[DEBUG] Left-half match found at: {player[0]}")
                        # cv2.circle(debug_minimap, player[0], 3, (255, 255, 0), -1)  # Yellow dot
                if not player:
                    p_height, p_width = PLAYER_TEMPLATE.shape
                    right_half_player = PLAYER_TEMPLATE[0:p_height, p_width //2+1 : p_width]
                    player = utils.multi_match(minimap, right_half_player, threshold=0.8)
                    if player:
                        find_right_half = True
                        # print(f"[DEBUG] Right-half match found at: {player[0]}")
                        # cv2.circle(debug_minimap, player[0], 3, (0, 255, 255), -1)  # Cyan dot
                if not player:
                    p_height, p_width = PLAYER_TEMPLATE.shape
                    right_half_player = PLAYER_TEMPLATE[p_height //2+1:p_height, 0 : p_width]
                    player = utils.multi_match(minimap, right_half_player, threshold=0.8)
                    if player:
                        find_bottom_half = True
                        # print(f"[DEBUG] Bottom-half match found at: {player[0]}")
                        # cv2.circle(debug_minimap, player[0], 3, (255, 0, 255), -1)  # Magenta dot
                # cv2.imwrite("debug_minimap_player_match.png", debug_minimap)
                if player:
                    # check is_standing
                    last_player_pos = config.player_pos
                    config.player_pos = utils.convert_to_relative(player[0], minimap)
                    if find_left_half:
                        config.player_pos = (config.player_pos[0]+2,config.player_pos[1])
                    if find_right_half:
                        config.player_pos = (config.player_pos[0]-2,config.player_pos[1])
                    if find_bottom_half:
                        config.player_pos = (config.player_pos[0],config.player_pos[1]-1)
                    done_check_is_standing = False
                    # print(config.player_pos)
                    # record if latest postion has been changed
                    if last_player_pos != config.player_pos or self.refresh_counting % 5 == 0:
                        self.latest_positions.append(config.player_pos)
                        if len(self.latest_positions) > self.MAX_LATEST_POSITION_AMOUNT:
                            self.latest_positions.pop(0)

                    # check is_standing by settins.platforms
                    if settings.platforms != '':
                        temp_platforms = settings.platforms.split("|")
                        for platform_y in temp_platforms:
                            is_bottom = False
                            not_in_any_platform = True
                            check_is_bottom = platform_y.split("b")
                            if len(check_is_bottom) == 2:
                                temp_xy = check_is_bottom[1].split("*")
                                platform_y = check_is_bottom[1]
                                is_bottom = True
                            else:
                                temp_xy = platform_y.split("*")
                            if len(temp_xy) == 1:
                                if abs(int(platform_y) - int(config.player_pos[1])) <= 0:
                                    config.player_states['is_standing'] = True
                                    config.player_states['movement_state'] = config.MOVEMENT_STATE_STANDING
                                    done_check_is_standing = True
                                    not_in_any_platform = False
                                    if is_bottom:
                                        config.player_states['in_bottom_platform'] = True
                                    else:
                                        config.player_states['in_bottom_platform'] = False
                                    break
                            else:
                                temp_x_range = temp_xy[0].split("~")
                                if abs(int(temp_xy[1]) - int(config.player_pos[1])) <= 0\
                                        and (int(temp_x_range[1]) >= config.player_pos[0] and int(temp_x_range[0]) <= config.player_pos[0]): 
                                    config.player_states['is_standing'] = True
                                    config.player_states['movement_state'] = config.MOVEMENT_STATE_STANDING
                                    done_check_is_standing = True
                                    not_in_any_platform = False
                                    if is_bottom:
                                        config.player_states['in_bottom_platform'] = True
                                    else:
                                        config.player_states['in_bottom_platform'] = False
                                    break
                        if not_in_any_platform == True:
                            config.player_states['in_bottom_platform'] = False
                    if last_player_pos[1] == config.player_pos[1] and not config.player_states['is_standing']:
                        self.check_is_standing_count += 1
                        if self.check_is_standing_count >= 8:
                            config.player_states['is_standing'] = True
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_STANDING
                            self.check_is_standing_count = 0
                    elif last_player_pos[1] != config.player_pos[1] and done_check_is_standing == False:
                        self.check_is_standing_count = 0
                        config.player_states['is_standing'] = False
                        if last_player_pos[1] < config.player_pos[1]:
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_FALLING
                        else:
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_JUMPING
                else:
                    if config.player_pos != (0,0): # check is last player_pos near the border
                        if config.player_pos[1] < 10:
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_JUMPING
                            config.player_pos = (config.player_pos[0],0)
                        if config.player_pos[0] < 50:
                            config.player_pos = (0,config.player_pos[1])
                            config.player_states['is_standing'] = True
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_STANDING
                        elif int(minimap.shape[1]) - config.player_pos[0] < 50:
                            config.player_pos = (int(minimap.shape[1]),config.player_pos[1])
                            config.player_states['is_standing'] = True
                            config.player_states['movement_state'] = config.MOVEMENT_STATE_STANDING
                
                # Package display information to be polled by GUI
                self.minimap = {
                    'minimap': minimap,
                    'rune_active': config.bot.rune_active,
                    'rune_pos': config.bot.rune_pos,
                    'path': config.path,
                    'player_pos': config.player_pos
                }

                if not self.ready:
                    self.ready = True
                self.refresh_counting = self.refresh_counting + 1
                if settings.rent_frenzy:
                    time.sleep(self.capture_gap_sec*4)
                else:
                    time.sleep(self.capture_gap_sec)
                

    def screenshot(self, tl_x = 0, tl_y = 0, width=0, height=0, delay=0.1):
        start = time.time()
        with mss.mss() as self.sct:
            try:
                frame = np.array(self.sct.grab(self.window))
                frame = frame[tl_y:tl_y+height, tl_x:tl_x+width]
                # print('use time : ',start - time.time())
                return frame
            except mss.exception.ScreenShotError:
                print(f'\n[!] Error while taking screenshot, retrying in {delay} second'
                    + ('s' if delay != 1 else ''))
                time.sleep(delay)
    
    def screenshot_in_bg(self,handle: HWND, tl_x = 0, tl_y = 0, width=0, height=0):
        if settings.full_screen:
            return self.screenshot(tl_x,tl_y,width,height)

        # 1. Get client size
        r = RECT()
        GetClientRect(handle, byref(r))
        width = width or (r.right - r.left)
        height = height or (r.bottom - r.top)

        # 2. Get client top-left corner in screen coordinates
        pt = wintypes.POINT(0, 0)
        ClientToScreen(handle, byref(pt))
        client_left = pt.x
        client_top = pt.y

        # 3. Create capture DC and bitmap
        screen_dc = GetDC(0)  # desktop DC (not window DC)
        mem_dc = CreateCompatibleDC(screen_dc)
        bmp = CreateCompatibleBitmap(screen_dc, width, height)
        SelectObject(mem_dc, bmp)

        # 4. Try PrintWindow first
        BitBlt(mem_dc, 0, 0, width, height, screen_dc,
           client_left + tl_x, client_top + tl_y, SRCCOPY | CAPTUREBLT)

         # 5. Extract pixels
        total_bytes = width * height * 4
        buffer = bytearray(total_bytes)
        byte_array = c_ubyte * total_bytes
        GetBitmapBits(bmp, total_bytes, byte_array.from_buffer(buffer))

        # 6. Cleanup
        DeleteObject(bmp)
        DeleteObject(mem_dc)
        ReleaseDC(handle, screen_dc)

        return np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, 4)
