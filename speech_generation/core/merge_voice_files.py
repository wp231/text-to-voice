import os
import ffmpeg
from ..utils.logger import logger

class MergeVoiceFiles:
    @staticmethod
    def merge(input_files: list, output_file: str) -> str|None:
        """
        使用 ffmpeg 將多個音頻文件合併為一個音頻文件
        :param input_files: 要合併的輸入音頻文件列表
        :param output_file: 合併後的輸出音頻文件路徑
        :return: 合併過程中的錯誤信息，如果沒有錯誤則返回 None
        """

        list_file = 'temp_merge_voice_file_list.txt'

        with open(list_file, 'w', encoding='utf-8') as f:
            for file in input_files:
                f.write(f"file '{file}'\n")

        try:
            loglevel = "error"

            _, error = ffmpeg.input(list_file, format='concat', safe=0) \
                .output(output_file, c='copy', loglevel=loglevel) \
                .run(capture_stderr=True, overwrite_output=True)
            
            if error:
                return error.decode("utf-8", errors="replace")

        finally:
            os.remove(list_file)