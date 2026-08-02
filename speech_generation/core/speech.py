import re
import os
import asyncio
import threading
import edge_tts
from pydub.utils import mediainfo
from ..utils.logger import logger

# 檢查音訊檔案與理論音訊時長的誤差率允許範圍
CHECK_VOICE_THRESHOLD_RATIO = 0.07
# 檢查重新生成音訊檔與原音訊檔大小比率允許範圍
CHECK_VOICE_SIZE_THRESHOLD_RATIO = 0.01
# 重新生成音訊檔最大重試次數
RETRY_MAX_COUNT = 3

FIXED_VOICE = "zh-CN-YunxiNeural"
FIXED_RATE = "+1%"
FIXED_PITCH = "+0Hz"
FIXED_VOLUME = "+100%"


class SpeechGenerationCancelled(Exception):
    """語音生成被使用者取消。"""


class Speech:
    def __init__(self, stop_event: threading.Event | None = None) -> None:
        self.stop_event = stop_event or threading.Event()
        self.__state_lock = threading.Lock()
        self.__loop: asyncio.AbstractEventLoop | None = None
        self.__task: asyncio.Task | None = None

    def cancel(self) -> None:
        """安全地取消目前正在執行的 edge-tts 非同步工作。"""
        self.stop_event.set()

        with self.__state_lock:
            loop = self.__loop
            task = self.__task

        if loop is not None and task is not None and not task.done():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                # 事件迴圈可能剛好已在另一個執行緒中關閉。
                pass

    def __raise_if_cancelled(self) -> None:
        if self.stop_event.is_set():
            raise SpeechGenerationCancelled()

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

    async def __async_generate(self, text: str, voice_file_name: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=FIXED_VOICE,
            rate=FIXED_RATE,
            pitch=FIXED_PITCH,
            volume=FIXED_VOLUME,
        )
        await communicate.save(voice_file_name)

    def __generate(self, text: str, voice_file_name: str):
        self.__raise_if_cancelled()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self.__async_generate(text, voice_file_name))

        with self.__state_lock:
            self.__loop = loop
            self.__task = task

        if self.stop_event.is_set():
            task.cancel()

        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError as exc:
            raise SpeechGenerationCancelled() from exc
        finally:
            with self.__state_lock:
                self.__task = None
                self.__loop = None

            # 確保 aiohttp/asyncio 建立的背景工作在關閉事件迴圈前完成清理。
            pending_tasks = asyncio.all_tasks(loop)
            for pending_task in pending_tasks:
                pending_task.cancel()
            if pending_tasks:
                loop.run_until_complete(
                    asyncio.gather(*pending_tasks, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
            asyncio.set_event_loop(None)
            loop.close()

    def generate(self, text: str, voice_file_name: str) -> bool:

        text = text.strip()
        if not text:
            return False

        self.__raise_if_cancelled()
        logger.debug(f"Generating voice file: {voice_file_name}")
        self.__generate(text, voice_file_name)
        self.__raise_if_cancelled()

        old_voice_file_size = os.path.getsize(voice_file_name)
        if self.__check_voice_file_integrity(text, voice_file_name):
            logger.debug(f"Voice file integrity check passed: {voice_file_name}")
            return True
        logger.debug(f"Voice file integrity check failed: {voice_file_name}")

        # 重新生成音訊檔
        retry_count = 0
        while retry_count < RETRY_MAX_COUNT:
            self.__raise_if_cancelled()

            logger.debug(f"Retrying to generate voice file: {voice_file_name}")
            self.__generate(text, voice_file_name)
            self.__raise_if_cancelled()

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
