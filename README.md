# TextToSound

借助微軟語音服務，將文字轉換為語音

## 安裝依賴

- 安裝 ffmpeg 並將其添加到環境變量中

- 安裝 Python 依賴
  ```shell
  pipenv install
  ```

## 使用方式

- 語音轉換
  ```shell
  python main.py -i input.txt [-o output.mp3]
  ```

- 設定請求語音服務的並發數量
  ```shell
  python main.py -i input.txt [-o output.mp3 -c 10]
  ```
