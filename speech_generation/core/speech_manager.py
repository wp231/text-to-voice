import os
import time
import queue
import threading
from typing import List
from .speech import Speech
from threading import Thread
from .text_queue import TextQueue
from ..utils.logger import LOG_FILE

# 設定日誌文件路徑
log_path = os.path.normpath(LOG_FILE)
log_path = os.path.dirname(log_path)

class SpeechManager:
    def __init__(self, input_file_queue: TextQueue, output_file: str)-> None:
        """
        初始化語音管理器
        :param input_queue: 輸入的文本隊列
        :param output_file: 輸出文件名
        """
        self.input_file_queue = input_file_queue
        self.output_file = output_file

        self.output_file_count = 1

        self.output_filename_queue = queue.Queue()
        self.error_output_filename_queue = queue.Queue()

    def __get_output_file_count(self) -> int:
        """
        獲取當前的輸出文件計數器，並將其增加 1
        """
        with self.input_file_queue.lock:
            self.output_file_count += 1
            return self.output_file_count - 1

    def __generate_voice(self) -> None:
        """
        從輸入隊列生成語音並將其保存到輸出文件中
        """
        speech = Speech()

        while True:
            text = self.input_file_queue.get()
            if text is None:
                break

            count = self.__get_output_file_count()
            file_name, file_extension = self.output_file.rsplit(".", 1)
            output_file_name = f"{file_name}_{count}.{file_extension}"

            log_file_name = os.path.basename(file_name)
            log_file = os.path.join(log_path, f"{log_file_name}_{count}.txt")
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(text)

            if speech.generate(text, output_file_name):
                self.output_filename_queue.put(output_file_name)
            else:
                self.error_output_filename_queue.put(output_file_name)

    def multi_threading_generate(self, thread_count: int):
        """
        使用多線程生成語音
        """
        threads: List[Thread] = []
        for _ in range(thread_count):
            thread = threading.Thread(target=self.__generate_voice)
            thread.start()
            threads.append(thread)
            time.sleep(1)

        try:
            while any(thread.is_alive() for thread in threads):
                time.sleep(1)
        except KeyboardInterrupt:
            raise KeyboardInterrupt("KeyboardInterrupt detected. Stopping threads...")

    def get_output_filename_queue(self) -> queue.Queue:
        """
        獲取生成成功的輸出文件名隊列
        """
        return self.output_filename_queue
    
    def get_error_output_filename_queue(self) -> queue.Queue:
        """
        獲取生成失敗的輸出文件名隊列
        """
        return self.error_output_filename_queue