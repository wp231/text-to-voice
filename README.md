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
  python main.py -i input.txt -o output.mp3
  ```

- 設定請求語音服務的並發數量
  ```shell
  python main.py -i input.txt -o output.mp3 -c 10
  ```

- 顯示所有可用的語音
  ```shell
  python main.py -l [zh-CN]
  ```

## 修改配置

透過修改 `config.json` 文件，可以修改語音的參數

- `voice_name`: 語音名稱
- `voice_pitch`: 語音音調
- `voice_volume`: 語音音量
- `voice_rate`: 語音速率

```json
{
    "voice_name": "zh-CN-YunxiNeural",
    "voice_pitch": 0,
    "voice_volume": 1.0,
    "voice_rate": 1
}
```
