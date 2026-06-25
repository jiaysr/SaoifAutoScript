# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import random
import time
from cached_property import cached_property

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_realm_raid, page_main
from tasks.Quiz.assets import QuizAssets
from tasks.ActivityShikigami.assets import ActivityShikigamiAssets
from tasks.DemonEncounter.data.answer import Answer
from tasks.Quiz.debug import Debugger, remove_symbols

from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer
from module.atom.image_grid import ImageGrid
from module.atom.image import RuleImage
from module.atom.click import RuleClick
from module.device.screenshot import Screenshot


class NoTicket(Exception):
    pass


class ScriptTask(GameUi, QuizAssets, ActivityShikigamiAssets, Debugger):

    def test(self):
        """测试方法：截图并保存区域图片"""
        from module.base.utils import save_image
        from pathlib import Path
        import time
        
        x = 1014
        y_start, y_end = 123, 522
        
        log_dir = Path('./log/fishing')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info('执行测试方法')
        img = self.screenshot()
        
        # 保存完整截图（使用项目方式）
        timestamp = int(time.time() * 1000)
        full_path = log_dir / f'full_{timestamp}.png'
        save_image(img, str(full_path))
        logger.info(f'完整截图已保存: {full_path}')
        
        # 保存单列图片
        region = img[y_start:y_end, x]
        
        # 打印所有坐标的颜色信息
        logger.info('单列颜色信息:')
        for i, color in enumerate(region):
            r, g, b = int(color[0]), int(color[1]), int(color[2])
            logger.info(f'  ({x}, {y_start + i}): RGB({r}, {g}, {b})')
        
        region = region.reshape(-1, 1, 3)  # 转为(height, 1, 3)
        region_path = log_dir / f'region_{timestamp}.png'
        save_image(region, str(region_path))
        logger.info(f'区域图片已保存: {region_path}')
        
        return img

    def test_nemu_ipc_color(self):
        logger.info('===== nemu_ipc 颜色采样测试 =====')
        logger.info(f'当前截图方式: {self.config.script.device.screenshot_method}')

        total_times = []
        for i in range(10):
            start = time.perf_counter()

            img = self.device.screenshot_nemu_ipc()
            h, w = img.shape[:2]

            colors = []
            for _ in range(10):
                x = random.randint(0, w - 1)
                y = random.randint(0, h - 1)
                r, g, b = [int(v) for v in img[y, x]]
                colors.append((x, y, r, g, b))

            elapsed = (time.perf_counter() - start) * 1000
            total_times.append(elapsed)

            info = '  '.join([f'({x},{y}) RGB({r},{g},{b})' for x, y, r, g, b in colors])
            logger.info(f'[{i+1:2d}] {elapsed:6.1f}ms | {info}')

        avg = sum(total_times) / len(total_times)
        logger.info(f'===== 完成: 平均 {avg:.1f}ms/次, 最短 {min(total_times):.1f}ms, 最长 {max(total_times):.1f}ms =====')

    def test_window_color(self):
        import ctypes
        from win32gui import GetWindowDC, ReleaseDC, GetWindowRect

        hwnd = 393554
        logger.info('===== GDI GetPixel 窗口像素直接读取测试 =====')
        logger.info(f'窗口句柄: {hwnd}')

        rect = GetWindowRect(hwnd)
        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]
        logger.info(f'窗口尺寸: {win_w}x{win_h}')

        total_times = []
        for i in range(10):
            start = time.perf_counter()

            hwndDc = GetWindowDC(hwnd)
            colors = []
            for _ in range(10):
                x = random.randint(0, win_w - 1)
                y = random.randint(0, win_h - 1)
                cref = ctypes.windll.gdi32.GetPixel(hwndDc, x, y)
                r = cref & 0xff
                g = (cref >> 8) & 0xff
                b = (cref >> 16) & 0xff
                colors.append((x, y, r, g, b))
            ReleaseDC(hwnd, hwndDc)

            elapsed = (time.perf_counter() - start) * 1000
            total_times.append(elapsed)

            info = '  '.join([f'({x},{y}) RGB({r},{g},{b})' for x, y, r, g, b in colors])
            logger.info(f'[{i+1:2d}] {elapsed:6.1f}ms | {info}')

        avg = sum(total_times) / len(total_times)
        logger.info(f'===== 完成: 平均 {avg:.1f}ms/次, 最短 {min(total_times):.1f}ms, 最长 {max(total_times):.1f}ms =====')

    def find_needle_window(self):
        import ctypes
        import time
        from win32gui import GetWindowDC, ReleaseDC

        hwnd = 393554
        target = (180, 254, 255)
        thr = 20
        logger.info('===== GDI 窗口找色 =====')
        logger.info(f'区域 x=1014~1015 y=123~522  目标 #{target[0]:02x}{target[1]:02x}{target[2]:02x}')

        img = self.device.screenshot_nemu_ipc()
        from module.base.utils import save_image
        from pathlib import Path
        log_dir = Path('./log/fishing')
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        h, w = img.shape[:2]
        save_image(img, str(log_dir / f'window_full_{ts}.png'))
        region = img[123:523, 1014:1016]
        save_image(region, str(log_dir / f'window_region_1014-1015_y123-522_{ts}.png'))
        logger.info(f'截图已保存至 log/fishing/ (win_w={w}, win_h={h})')

        while True:
            start = time.perf_counter()

            hwndDc = GetWindowDC(hwnd)
            found = None
            for x in range(1014, 1015):
                for y in range(123, 523):
                    cref = ctypes.windll.gdi32.GetPixel(hwndDc, x, y)
                    r = cref & 0xff
                    g = (cref >> 8) & 0xff
                    b = (cref >> 16) & 0xff
                    if max(r, target[0]) - min(r, target[0]) <= thr \
                       and max(g, target[1]) - min(g, target[1]) <= thr \
                       and max(b, target[2]) - min(b, target[2]) <= thr:
                        found = (x, y)
                        break
                if found:
                    break
            ReleaseDC(hwnd, hwndDc)

            elapsed = (time.perf_counter() - start) * 1000
            if found:
                logger.info(f'坐标 ({found[0]},{found[1]})  ({elapsed:.1f}ms)')
            else:
                logger.info(f'未找到  ({elapsed:.1f}ms)')

            remain = 0.005 - (time.perf_counter() - start)
            if remain > 0:
                time.sleep(remain)

    def find_needle_nemu_ipc(self):
        import numpy as np
        import time

        logger.info('===== nemu_ipc 窗口找色 =====')
        logger.info(f'区域 x=1014~1015 y=123~522  目标 (255,254,180) 硬匹配')

        while True:
            start = time.perf_counter()
            img = self.device.screenshot_nemu_ipc()
            crop = img[123:523, 1014:1016]
            mask = np.all(crop == (180, 254, 255), axis=2)
            matches = np.argwhere(mask)
            found = None
            if len(matches):
                y, x = matches[0]
                found = (1014 + x, 123 + y)
            elapsed = (time.perf_counter() - start) * 1000
            if found:
                logger.info(f'坐标 ({found[0]},{found[1]})  ({elapsed:.2f}ms)')
            else:
                logger.info(f'未找到  ({elapsed:.2f}ms)')

    def run(self):
        import numpy as np

        logger.info('开始钓鱼（nemu_ipc 轮询）')

        while True:
            img = self.device.screenshot_nemu_ipc()
            crop = img[123:523, 1014:1016]
            g = crop[:, :, 1].astype(np.int16)
            b = crop[:, :, 2].astype(np.int16)
            r = crop[:, :, 0].astype(np.int16)
            perfect = np.argwhere((g > 225) & (r < 210) & (b < 165) & ((g - r) > 15) & ((g - b) > 60))
            if not len(perfect):
                continue
            p_start = 123 + perfect[0][0]
            p_end = 123 + perfect[-1][0]
            logger.info(f'完美区域: {p_start}-{p_end}')

            while True:
                img = self.device.screenshot_nemu_ipc()
                needle = np.argwhere(np.all(img[123:523, 1014:1016] == (180, 254, 255), axis=2))
                if len(needle):
                    pos = 123 + needle[0][0]
                    logger.info(f'指针位置: {pos}')
                    if p_start +5 <= pos <= p_end +5:
                        logger.info(f'命中! pos={pos}')
                        self.device.click(1173, 510)
                        time.sleep(1)
                        break


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
