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
    
    def run(self):
        import numpy as np
        
        x = 1014
        y_start, y_end = 123, 522
        
        # 指针颜色 #b4feff -> BGR(255, 254, 180)
        needle_color = np.array([180, 254, 255])
        needle_threshold = 20
        
        def find_needle(region):
            """查找指针位置"""
            diff = np.abs(region.astype(np.int16) - needle_color)
            mask = np.all(diff < needle_threshold, axis=1)
            indices = np.where(mask)[0]
            if len(indices) > 0:
                return y_start + indices[0]
            return None
        
        def find_perfect_region(region):
            """查找完美区域"""
            g = region[:, 1].astype(np.int16)
            b = region[:, 2].astype(np.int16)
            r = region[:, 0].astype(np.int16)
            mask = (g > 225) & (r < 210) & (b < 165) & ((g - r) > 15) & ((g - b) > 60)
            indices = np.where(mask)[0]
            if len(indices) > 0:
                return y_start + indices[0], y_start + indices[-1]
            return None, None
        
        def calc_wait_time(pos, speed, target_min, target_max):
            """
            计算指针到达完美区域需要的等待时间
            pos: 当前指针位置
            speed: 速度（正=向下，负=向上）
            target_min: 完美区域上边界
            target_max: 完美区域下边界
            """
            # 指针移动方向：speed > 0 向下，speed < 0 向上
            
            if speed > 0:
                # 指针向下移动
                if pos <= target_max:
                    # 指针在完美区域上方或内部，可以直接到达
                    if pos >= target_min:
                        return 0  # 已经在完美区域内
                    return (target_min - pos) / speed
                else:
                    # 指针已经过了完美区域，需要到底部再反向向上
                    to_bottom = y_end - pos
                    back_to_target = y_end - target_max
                    return (to_bottom + back_to_target) / abs(speed)
            else:
                # 指针向上移动
                if pos >= target_min:
                    # 指针在完美区域下方或内部，可以直接到达
                    if pos <= target_max:
                        return 0  # 已经在完美区域内
                    return (pos - target_max) / abs(speed)
                else:
                    # 指针已经过了完美区域，需要到顶部再反向向下
                    to_top = pos - y_start
                    back_to_target = target_min - y_start
                    return (to_top + back_to_target) / abs(speed)
        
        logger.info('开始钓鱼循环（预测模式）')
        logger.info(f'监测区域: x={x}, y={y_start}-{y_end}')
        
        loop_count = 0
        
        while True:
            loop_count += 1
            logger.info(f'=== 大循环 {loop_count} ===')
            
            # 步骤1：找完美区域
            perfect_min = None
            perfect_max = None
            while perfect_min is None:
                img = self.screenshot()
                region = img[y_start:y_end, x]
                p_start, p_end = find_perfect_region(region)
                if p_start is not None:
                    perfect_min, perfect_max = p_start, p_end
                    perfect_center = (p_start + p_end) / 2
                    logger.info(f'✓ 完美区域: {p_start}-{p_end}, 中心: {perfect_center}')
                else:
                    time.sleep(0.01)
            
            # 步骤2：计算速度 - 截取两个时间点
            # 第一次截图
            img1 = self.screenshot()
            region1 = img1[y_start:y_end, x]
            pos1 = find_needle(region1)
            t1 = time.time()
            
            if pos1 is None:
                logger.info('第一次未找到指针，等待...')
                time.sleep(0.05)
                continue
            
            # 等待固定时间
            wait_dt = 0.1
            time.sleep(wait_dt)
            
            # 第二次截图
            img2 = self.screenshot()
            region2 = img2[y_start:y_end, x]
            pos2 = find_needle(region2)
            t2 = time.time()
            
            if pos2 is None:
                logger.info('第二次未找到指针，等待...')
                time.sleep(0.05)
                continue
            
            # 使用固定等待时间计算速度（更准确）
            # 因为t2-t1包含了截图耗时，而我们实际只等待了wait_dt
            speed = (pos2 - pos1) / wait_dt
            direction = "向上" if speed < 0 else "向下"
            logger.info(f'指针位置: {pos1} -> {pos2}, 速度: {speed:.1f} px/s ({direction})')
            
            # 步骤3：计算到达完美区域需要的时间
            # 使用pos1作为起点，因为速度是从pos1开始计算的
            wait_time = calc_wait_time(pos1, speed, perfect_min, perfect_max)
            
            # 减去已经过去的时间（从pos1到现在）
            elapsed = time.time() - t1
            wait_time = max(0, wait_time - elapsed)
            
            if wait_time == 0:
                logger.info('指针已在完美区域内或已到达，立即点击!')
            else:
                logger.info(f'等待时间: {wait_time:.3f}s (已过{elapsed:.3f}s)')
                time.sleep(wait_time)
            
            # 步骤4：点击
            logger.info(f'>>> 点击! (1173, 510)')
            self.device.click(1173, 510)
            
            logger.info('点击完成，进入下一个大循环')
            time.sleep(0.5)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
