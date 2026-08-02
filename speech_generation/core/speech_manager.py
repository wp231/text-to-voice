import os
import sys
import time
import queue
import threading
from typing import List
from .speech import Speech, SpeechGenerationCancelled
from threading import Thread
from .text_queue import TextQueue
from ..utils.logger import LOG_FILE, logger

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

        self.stop_event = threading.Event()
        self.speeches: List[Speech] = []
        self.speeches_lock = threading.Lock()

        self.total_count = input_file_queue.get_length()
        self.completed_count = 0
        self.progress_lock = threading.Lock()
        self.progress_started = False

    def __get_output_file_count(self) -> int:
        """
        獲取當前的輸出文件計數器，並將其增加 1
        """
        with self.input_file_queue.lock:
            self.output_file_count += 1
            return self.output_file_count - 1

    def __render_progress(self, finished: bool = False) -> None:
        """在同一行顯示整體生成進度，不引入額外依賴。"""
        with self.progress_lock:
            self.progress_started = True
            total = self.total_count
            completed = self.completed_count
            ratio = completed / total if total else 1.0
            width = 30
            filled = min(width, int(width * ratio))
            bar = "#" * filled + "-" * (width - filled)
            percent = ratio * 100

            sys.stdout.write(
                f"\r[PROGRESS] [{bar}] {completed}/{total} ({percent:5.1f}%)"
            )
            if finished:
                sys.stdout.write("\n")
            sys.stdout.flush()

    def __advance_progress(self) -> None:
        with self.progress_lock:
            self.completed_count += 1
        self.__render_progress()

    def __register_speech(self, speech: Speech) -> None:
        with self.speeches_lock:
            self.speeches.append(speech)

    def __unregister_speech(self, speech: Speech) -> None:
        with self.speeches_lock:
            if speech in self.speeches:
                self.speeches.remove(speech)

    def cancel(self) -> None:
        """通知所有工作執行緒停止，並取消正在進行的非同步請求。"""
        self.stop_event.set()
        with self.speeches_lock:
            speeches = list(self.speeches)

        for speech in speeches:
            speech.cancel()

    def __generate_voice(self) -> None:
        """
        從輸入隊列生成語音並將其保存到輸出文件中
        """
        speech = Speech(self.stop_event)
        self.__register_speech(speech)

        try:
            while not self.stop_event.is_set():
                text = self.input_file_queue.get()
                if text is None or self.stop_event.is_set():
                    break

                count = self.__get_output_file_count()
                file_name, file_extension = self.output_file.rsplit(".", 1)
                output_file_name = f"{file_name}_{count}.{file_extension}"

                log_file_name = os.path.basename(file_name)
                log_file = os.path.join(log_path, f"{log_file_name}_{count}.txt")
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(text)

                try:
                    if speech.generate(text, output_file_name):
                        self.output_filename_queue.put(output_file_name)
                    else:
                        self.error_output_filename_queue.put(output_file_name)
                except SpeechGenerationCancelled:
                    if os.path.exists(output_file_name):
                        os.remove(output_file_name)
                    break
                except Exception:
                    logger.exception(f"Generation failed for file {output_file_name}")
                    self.error_output_filename_queue.put(output_file_name)
                finally:
                    if not self.stop_event.is_set():
                        self.__advance_progress()
        finally:
            self.__unregister_speech(speech)

    def __join_threads(self, threads: List[Thread], ignore_interrupts: bool = False) -> None:
        """等待所有工作執行緒結束；清理階段可忽略重複的 Ctrl+C。"""
        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                try:
                    thread.join(timeout=0.1)
                except KeyboardInterrupt:
                    if not ignore_interrupts:
                        raise
                    self.cancel()

    def multi_threading_generate(self, thread_count: int) -> None:
        """
        使用多線程生成語音
        """
        threads: List[Thread] = []
        interrupted = False

        self.__render_progress()

        try:
            for _ in range(thread_count):
                thread = threading.Thread(target=self.__generate_voice)
                thread.start()
                threads.append(thread)
                time.sleep(1)

            self.__join_threads(threads)
        except KeyboardInterrupt:
            interrupted = True
            self.cancel()
            self.__join_threads(threads, ignore_interrupts=True)
        finally:
            if self.progress_started:
                self.__render_progress(finished=True)

        if interrupted:
            raise KeyboardInterrupt()

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
