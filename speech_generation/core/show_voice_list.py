import re
import asyncio
from msspeech import MSSpeech
from collections import defaultdict

class ShowVoiceList:
    """
    顯示可用語音的列表
    """

    @staticmethod
    def __print_format_voice_list(voice_data) -> None:
        voices = defaultdict(list)

        pattern = r"\(([^,]+), ([^)]+)\)"
        matches = re.findall(pattern, voice_data)

        for locale, voice in matches:
            voices[locale].append(voice)

        for locale, voice_names in voices.items():
            print(locale)
            for i, voice in enumerate(voice_names):
                if i == len(voice_names) - 1:
                    print(f"  └─ {locale}-{voice}")
                else:
                    print(f"  ├─ {locale}-{voice}")


    @staticmethod
    async def __show_voice_list(locale: str = "") -> None:
        mss = MSSpeech()

        output = ""
        voices = await mss.get_voices_list()
        for voice in voices:
            if locale.lower() in voice["Locale"].lower():
                output += voice["Name"] + "\n"
            elif locale == "":
                output += voice["Name"] + "\n"

        ShowVoiceList.__print_format_voice_list(output)


    @staticmethod
    def print(name: str = "all") -> None:
        loop = asyncio.get_event_loop()
        if name == 'all':
            loop.run_until_complete(ShowVoiceList.__show_voice_list())
        else:
            loop.run_until_complete(ShowVoiceList.__show_voice_list(name))
    