from .speech import FIXED_PITCH, FIXED_RATE, FIXED_VOICE, FIXED_VOLUME


class ShowVoiceList:
    """顯示專案唯一使用的固定語音設定。"""

    @staticmethod
    def print(name: str = "all") -> None:
        _ = name
        print(FIXED_VOICE)
        print(f"  rate: {FIXED_RATE}")
        print(f"  pitch: {FIXED_PITCH}")
        print(f"  volume: {FIXED_VOLUME}")
