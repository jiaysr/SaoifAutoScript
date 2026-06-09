# This Python file uses the following encoding: utf-8
# 图片匹配测试脚本

import time
from module.logger import logger
from module.exception import TaskEnd
from tasks.GameUi.game_ui import GameUi
from tasks.IamgeTest.assets import IamgeTestAssets


class ScriptTask(GameUi, IamgeTestAssets):

    def run(self) -> None:
        """循环测试图片匹配"""
        logger.info("开始图片匹配测试...")
        logger.info("按 Ctrl+C 停止测试")

        count = 0
        while 1:
            self.screenshot()

            # 测试 I_LOGO 是否出现
            if self.appear(self.I_LOGO):
                count += 1
                logger.info(f"[{count}] ✓ 匹配成功! I_LOGO 出现了")
                # 如果需要测试点击，取消下面的注释（带频率控制）
                self.click(self.I_LOGO, interval=3)
            else:
                logger.info("✗ 未匹配到 I_LOGO")

            time.sleep(1)  # 每秒检测一次

        raise TaskEnd('IamgeTest end')


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)
    t.run()
