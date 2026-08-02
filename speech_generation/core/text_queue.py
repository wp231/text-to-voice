import re
import os
import threading

TEMP_FILE_PATH = "text_queue_temp.txt"
PUNCTUATION_PREFIX = "‛‘‟“〝‵({〈《「『【〔［︵︷︹︻︽︿﹁﹃﹙﹛﹝﹤（｟＜｛❬❮❰〖〘〚〈‹«｢⌃"
PUNCTUATION_SUFFIX = ",‚，﹐。'\"!！﹗?？﹖；﹔~〜…｀＂’”〞′)}〉》」』】〕］︶︸︺︼︾﹀﹂﹄﹚﹜﹞﹥）｠＞｝❭❯❱〗〙〛〉›»｣⌄"

TEXT_SPLIT_SIZE = 3000

class TextQueue:
    '''
    讀取文本檔案，並將其分割成小段以便於處理
    '''
    def __init__(self, file_path: str, chunk_size: int = TEXT_SPLIT_SIZE, encoding: str = 'utf-8'):
        self.index = 0
        self.position = 0
        self.is_end = False
        self.encoding = encoding
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.lock = threading.Lock()
        self.temp_file_path = TEMP_FILE_PATH

        self.__preprocess_file()
        self.length = self.__calculate_length()

    def __preprocess_file(self):
        '''預處理檔案，去除空白，加上標點符號'''
        with open(self.file_path, 'r', encoding=self.encoding) as file:
            with open(self.temp_file_path, 'w', encoding=self.encoding) as new_file:
                for line in file:
                    if line[-1] == "\n":
                        line = line[:-1]

                    line = line.strip()

                    if line != "" and line[-1] not in PUNCTUATION_SUFFIX:
                        line += "。"

                    line = re.sub(r"\s+", "", line)

                    new_file.write(line)

    def __calculate_length(self) -> int:
        '''計算隊列長度'''
        length = 0
        while True:
            text = self.get()
            if text is None:
                break
            length += 1

        self.index = 0
        self.position = 0
        self.is_end = False
        return length

    def get_length(self) -> int:
        return self.length

    def get(self) -> str | None:
        with self.lock:
            if self.is_end:
                return None

            self.index += 1
            with open(self.temp_file_path, 'r', encoding=self.encoding) as file:
                file.seek(self.position)
                text = file.read(self.chunk_size)

                if not text:
                    self.is_end = True
                    return None

                for i in range(len(text) - 1, 0, -1):
                    if i == 0:
                        break
                    if text[i] in PUNCTUATION_PREFIX:
                        text = text[:i]
                        break
                    elif text[i] in PUNCTUATION_SUFFIX:
                        text = text[:i+1]
                        break

                self.position += len(text.encode(self.encoding))
                return text

    def __del__(self):
        os.remove(self.temp_file_path)


if __name__ == "__main__":
    text_queue = TextQueue("test.txt", 60)

    print(text_queue.get_length())

    while True:
        text = text_queue.get()
        if text is None:
            break
        print(text)
