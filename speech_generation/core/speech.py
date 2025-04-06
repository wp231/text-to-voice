import re
import os
import asyncio
from msspeech import MSSpeech
from pydub.utils import mediainfo
from ..utils.logger import logger
from ..utils.config_dao import config_dao

# 檢查音訊檔案與理論音訊時長的誤差率允許範圍
CHECK_VOICE_THRESHOLD_RATIO = 0.07
# 檢查重新生成音訊檔與原音訊檔大小比率允許範圍
CHECK_VOICE_SIZE_THRESHOLD_RATIO = 0.01
# 重新生成音訊檔最大重試次數
RETRY_MAX_COUNT = 3


class Speech:
    def __init__(self) -> None:
        self.is_initialized = False
        self.mss = MSSpeech()

    def __count_text_words(self, text: str) -> int:
        """計算文字檔案內的字數"""

        length = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9，。！？：…、；．‧–—]', text))
        return length

    def __get_voice_duration(self, file_path: str) -> float:
        """獲取音訊檔案長度（秒）"""

        info = mediainfo(file_path)
        return float(info['duration'])

    def __check_voice_file_integrity(self, text: str, voice_file_name: str, threshold_ratio=CHECK_VOICE_THRESHOLD_RATIO) -> bool:
        """檢查音訊檔案完整性"""

        text_length = self.__count_text_words(text)
        voice_duration = self.__get_voice_duration(voice_file_name)

        # 理論音訊時長（秒） = 0.1949 * 字數 + 4.98
        theoretical_voice_duration = 0.1949 * text_length + 4.98
        # 誤差秒數
        error_duration = abs(theoretical_voice_duration - voice_duration)
        # 誤差率
        error_ratio = error_duration / theoretical_voice_duration

        if error_ratio < threshold_ratio:
            return True
        else:
            return False

    async def __initialize(self):
        await self.mss.set_voice(config_dao.get_voice_name())
        await self.mss.set_pitch(config_dao.get_voice_pitch())
        await self.mss.set_volume(config_dao.get_voice_volume())
        await self.mss.set_rate(config_dao.get_voice_rate())
        self.is_initialized = True

    async def __async_generate(self, text: str, voice_file_name: str):
        if not self.is_initialized:
            await self.__initialize()

        await self.mss.synthesize(text, voice_file_name)

    def __generate(self, text: str, voice_file_name: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self.__async_generate(text, voice_file_name))
        finally:
            loop.close()

    def generate(self, text: str, voice_file_name: str) -> bool:

        text = text.strip()
        if not text:
            return False

        logger.debug(f"Generating voice file: {voice_file_name}")
        self.__generate(text, voice_file_name)
        old_voice_file_size = os.path.getsize(voice_file_name)
        if self.__check_voice_file_integrity(text, voice_file_name):
            logger.debug(f"Voice file integrity check passed: {voice_file_name}")
            return True
        logger.debug(f"Voice file integrity check failed: {voice_file_name}")

        # 重新生成音訊檔
        retry_count = 0
        while retry_count < RETRY_MAX_COUNT:

            logger.debug(f"Retrying to generate voice file: {voice_file_name}")
            self.__generate(text, voice_file_name)
            new_voice_file_size = os.path.getsize(voice_file_name)
            if self.__check_voice_file_integrity(text, voice_file_name):
                logger.debug(f"Voice file integrity check passed on retry: {voice_file_name}")
                return True
            logger.debug(f"Voice file integrity check failed on retry: {voice_file_name}")
            
            # 雖然無法滿足理論音訊時長誤差率，但檔案大小差異不大，視為生成成功
            size_diff_ratio = abs(new_voice_file_size - old_voice_file_size) / old_voice_file_size
            if size_diff_ratio < CHECK_VOICE_SIZE_THRESHOLD_RATIO:
                logger.debug(f"Voice file size check passed: {voice_file_name}")
                return True
            logger.debug(f"Voice file size check failed: {voice_file_name}")
            
            old_voice_file_size = new_voice_file_size
            retry_count += 1

        return False
