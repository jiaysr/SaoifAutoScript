# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import os
import random
import time
import cv2
from cached_property import cached_property
from pydantic.v1.datetime_parse import time_expr

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_realm_raid, page_main
from tasks.Quiz.assets import QuizAssets
from tasks.ActivityShikigami.assets import ActivityShikigamiAssets
from tasks.DemonEncounter.data.answer import Answer
from tasks.Quiz.debug import Debugger, remove_symbols

from tasks.Fishing.assets import FishingAssets
from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer
from module.atom.image_grid import ImageGrid
from module.atom.image import RuleImage
from module.atom.click import RuleClick
from module.device.screenshot import Screenshot


class NoTicket(Exception):
    pass


class ScriptTask(GameUi, FishingAssets, QuizAssets, ActivityShikigamiAssets, Debugger):

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

    @staticmethod
    def _parse_colors(data: str):
        """解析多点比色字符串 'x|y|RRGGBB,...' 为 [(x,y,(R,G,B)), ...]"""
        result = []
        for part in data.split(','):
            x_str, y_str, hex_str = part.split('|')
            x, y = int(x_str), int(y_str)
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            result.append((x, y, (r, g, b)))
        return result

    def _check_colors(self, img, points, tol=15):
        """检查所有颜色点是否匹配，返回匹配数/总数
        参考色为RGB，图像为BGR，对比时交换R/B通道"""
        match = 0
        for x, y, (r, g, b) in points:
            pixel = img[y, x]
            if abs(int(pixel[0]) - b) <= tol and abs(int(pixel[1]) - g) <= tol and abs(int(pixel[2]) - r) <= tol:
                match += 1
        return match, len(points)

    def _dump_colors(self, img, points, label):
        """打印每个点的实际颜色 vs 参考颜色"""
        for x, y, (r, g, b) in points:
            p = img[y, x]
            logger.info(f'  {label} ({x},{y})  参考=({r:3d},{g:3d},{b:3d}) '
                        f'实际=({int(p[0]):3d},{int(p[1]):3d},{int(p[2]):3d}) '
                        f'差={abs(int(p[0])-r):2d},{abs(int(p[1])-g):2d},{abs(int(p[2])-b):2d}')

    def run(self):
        import numpy as np

        do1_pts = self._parse_colors(
            "1182|485|CFCF00,1180|496|DEDD00,1179|508|B57536,1179|517|F3F307,"
            "1178|530|FFFF02,1177|547|7B4826,1157|546|F7F74A,1155|549|F0F057,1205|548|C8B7A6"
        )
        do2_pts = self._parse_colors(
            "1187|494|255C7D,1174|502|594430,1161|508|245C7C,1163|520|27657D,"
            "1162|530|5D5C56,1163|539|376478,1183|538|296A7D,1195|536|4C6F77,1206|527|4C2A11,1211|512|1B5179"
        )
        do3_pts = self._parse_colors(
            "1183|494|6D6D00,1182|509|502F16,1181|520|797901,1177|536|7F7F01,"
            "1157|535|767602,1176|547|5F4A3D,1181|553|412716,1186|548|492F1E,1199|542|4C2B17"
        )
        do4_pts=self._parse_colors(
            "1186|494|46B4F8,1168|515|51D4FB,1165|526|50CEFB,1165|538|D7E0E0,1178|538|57D3FA,1199|536|BA6532,1202|534|DDDDDD,1202|519|B1DCEB,1193|501|4EC8FB"
        )
        target_pts=self._parse_colors(
            "499|108|FBF9F7,499|109|FBF9F7,499|113|FBF9F7,499|116|FBF9F7,"
            "499|118|FBF9F7,499|119|FBF9F7,503|119|F9F7F7,505|118|3434DD,500|109|5C5CE1"
        )

        success_count = 0
        logger.info('=== 开始钓鱼 ===')
        self.device.disable_stuck_detection()

        self.screenshot()
        logger.info('首帧颜色采样:')
        self._dump_colors(self.device.image, do1_pts, 'DO1')
        self._dump_colors(self.device.image, do2_pts, 'DO2')
        self._dump_colors(self.device.image, do3_pts, 'DO3')
        self._dump_colors(self.device.image, do4_pts, 'DO4')
        self._dump_colors(self.device.image, target_pts, 'Target')

        end_time = time.time() + 45
        loop_count = 0
        clone_skip = 0

        while time.time() < end_time:
            loop_count += 1
            self.screenshot()
            img = self.device.image

            m1, n1 = self._check_colors(img, do1_pts)
            m4, n4 = self._check_colors(img, do4_pts)
            m3, n3 = self._check_colors(img, do3_pts)
            mt, nt = self._check_colors(img, target_pts)
            do1 = m1 >= n1 * 0.6
            do4 = m4 >= n4 * 0.6
            do3_matched = m3 >= n3 * 0.6
            text_matched = mt >= nt * 0.6

            if do1:
                logger.info(f'点击开始')
                self.device.click(1173, 510)

            if do4:
                logger.info(f'提竿')
                self.device.click(1173, 510)

            if text_matched and not do3_matched:
                crop = img[123:523, 1014:1016]
                g = crop[:, :, 1].astype(np.int16)
                b = crop[:, :, 2].astype(np.int16)
                r = crop[:, :, 0].astype(np.int16)
                perfect = np.argwhere((g > 225) & (r < 210) & (b < 165) & ((g - r) > 15) & ((g - b) > 60))
                if len(perfect):
                    p_start = 123 + perfect[0][0]
                    p_end = 123 + perfect[-1][0]
                    logger.info(f'完美区域: {p_start}-{p_end}')
                    needle_end = time.time() + 6
                    while time.time() < needle_end:
                        nd = np.argwhere(np.all(
                            self.device.screenshot_nemu_ipc()[123:523, 1014:1016] == (180, 254, 255), axis=2))
                        if len(nd):
                            pos = 123 + nd[0][0]
                            if p_start + 5 <= pos <= p_end + 5:
                                logger.info(f'命中! pos={pos}')
                                self.device.click(1173, 510)
                                time.sleep(1)
                                break
                        time.sleep(0.005)

            if not text_matched and do3_matched:
                clone_skip += 1
                if clone_skip >= 5:
                    clone_skip = 0
                    if os.path.exists(self.I_CLONE.file):
                        self.device.image = img
                        if self.appear(self.I_CLONE):
                            logger.info(f'钓鱼成功! +1')
                            self.appear_then_click(self.I_CLONE)
                            success_count += 1
                            logger.info(f'共钓鱼:{success_count}')
                            end_time = time.time() + 45 
                            time.sleep(1)

            time.sleep(0.03)

        logger.info(f'========== 结束，共钓鱼 {success_count} 次 ==========')


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
