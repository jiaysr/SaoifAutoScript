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
        
        # 指针颜色 #b4feff -> RGB(180, 254, 255)
        needle_color = np.array([180, 254, 255])
        needle_threshold = 20
        
        def find_needle(region):
            diff = np.abs(region.astype(np.int16) - needle_color)
            mask = np.all(diff < needle_threshold, axis=1)
            indices = np.where(mask)[0]
            if len(indices) > 0:
                return y_start + indices[0]
            return None
        
        def find_perfect_region(region):
            g = region[:, 1].astype(np.int16)
            b = region[:, 2].astype(np.int16)
            r = region[:, 0].astype(np.int16)
            mask = (g > 225) & (r < 210) & (b < 165) & ((g - r) > 15) & ((g - b) > 60)
            indices = np.where(mask)[0]
            if len(indices) > 0:
                return y_start + indices[0], y_start + indices[-1]
            return None, None
        
        def time_to_hit(pos, speed, target_y):
            """
            计算指针首次到达 target_y 所需时间，考虑 y_start~y_end 间往返运动
            """
            if speed > 0:
                if target_y >= pos:
                    return (target_y - pos) / speed
                else:
                    return (y_end - pos + y_end - target_y) / speed
            else:
                if target_y <= pos:
                    return (pos - target_y) / abs(speed)
                else:
                    return (pos - y_start + target_y - y_start) / abs(speed)
        
        logger.info('开始钓鱼循环（纯预测模式）')
        logger.info(f'监测区域: x={x}, y={y_start}-{y_end}')
        
        loop_count = 0
        
        while True:
            loop_count += 1
            logger.info(f'=== 大循环 {loop_count} ===')
            
            # 步骤1：找完美区域
            perfect_min = perfect_max = None
            while perfect_min is None:
                img = self.screenshot()
                region = img[y_start:y_end, x]
                p_start, p_end = find_perfect_region(region)
                if p_start is not None:
                    perfect_min, perfect_max = p_start, p_end
                    perfect_center = (p_start + p_end) / 2
                    logger.info(f'✓ 完美区域: {p_start}-{p_end}, 中心: {perfect_center:.1f}')
                else:
                    time.sleep(0.01)
            
            # 步骤2：连续采样测速（用实际时间差）
            samples = []
            for _ in range(6):
                img = self.screenshot()
                now = time.time()
                region = img[y_start:y_end, x]
                pos = find_needle(region)
                if pos is not None:
                    samples.append((pos, now))
                    if len(samples) >= 2:
                        break
                time.sleep(0.03)
            
            if len(samples) < 2:
                logger.info('未找到指针，重试...')
                continue
            
            # 继续采样到总跨度 >= 0.3s，保证速度精度
            t_start = samples[0][1]
            while len(samples) < 6:
                now = time.time()
                if now - t_start > 3.0:
                    break
                time.sleep(0.03)
                img = self.screenshot()
                now = time.time()
                region = img[y_start:y_end, x]
                pos = find_needle(region)
                if pos is not None:
                    samples.append((pos, now))
            
            # 最小二乘法拟合速度（用实际时间差）
            positions = np.array([s[0] for s in samples])
            times = np.array([s[1] for s in samples])
            speed = np.polyfit(times - times[0], positions, 1)[0]
            direction = "向上" if speed < 0 else "向下"
            logger.info(f'速度: {speed:.1f} px/s ({direction}), {len(samples)} 个样本, '
                        f'跨度 {times[-1]-times[0]:.3f}s')
            
            # 如果速度异常小（指针已停或接近停止），跳过本轮
            if abs(speed) < 10:
                logger.info('速度异常小，等待...')
                time.sleep(0.3)
                continue
            
            # 步骤3：计算等待时间并点击
            last_pos, last_time = samples[-1]
            hit_time = time_to_hit(last_pos, speed, perfect_center)
            if hit_time >= 5.0:
                logger.info(f'预测需要 {hit_time:.2f}s，超出 5s 限制，等下次机会')
                time.sleep(0.5)
                continue
            
            elapsed = time.time() - last_time
            wait_time = max(0, hit_time - elapsed)
            logger.info(f'等待 {wait_time:.3f}s (pos={last_pos}, target={perfect_center:.1f})')
            time.sleep(wait_time)
            
            # 步骤4：点击
            logger.info(f'>>> 点击! (1173, 510)')
            self.device.click(1173, 510)
            
            logger.info('点击完成')
            time.sleep(0.5)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
