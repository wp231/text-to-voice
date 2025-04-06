import os
import re
import sys
import os.path
import argparse
from typing import List
from speech_generation.utils.logger import logger
from speech_generation.core.text_queue import TextQueue
from speech_generation.core.speech_manager import SpeechManager
from speech_generation.core.show_voice_list import ShowVoiceList
from speech_generation.core.merge_voice_files import MergeVoiceFiles

DEFAULT_THREADS = 5
DEFAULT_OUTPUT_PATH = "voice/"

def create_output_folder(file_path: str) -> None:
    dir_path = os.path.dirname(file_path)

    if dir_path == "" or dir_path == ".":
        return

    os.makedirs(dir_path, exist_ok=True)

def extract_number(filename: str) -> int:
    """Extract number from filename"""
    filename = os.path.basename(filename)
    filename, _ = os.path.splitext(filename)
    matches = re.findall(r'\d+', filename)
    return int(matches[-1]) if matches else 0

# ================== Main Function ==================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="This script processes a text file and converts it into a voice file (MP3)."
    )

    parser.add_argument("-i", "--input", type=str, metavar="FILENAME",
                        help="Input txt file name (e.g., a.txt)")
    parser.add_argument("-o", "--output", type=str, metavar="FILENAME",
                        help="Output voice file name (e.g., a.mp3). Default is 'voice/<Input_file_name>.mp3'")
    parser.add_argument("-m", "--merge", action="store_true",
                        help="Merge all output files into one file")
    parser.add_argument("-c", "--concurrencies", type=int, metavar="NUMS",
                        help="Number of threads to use. Default is 5 if not specified.")
    parser.add_argument("-l", "--list", type=str, metavar="LOCALE", nargs='?', const='all',
                        help="Show all available voice list or the voice list of the specified locale")

    parser.add_argument("positional_input", nargs="?", help="Positional input file name (e.g., input.txt)")
    parser.add_argument("positional_output", nargs="?", help="Optional positional output file name (e.g., output.mp3)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        exit(1)

    # list arguments
    if args.list:
        other_args = {k: v for k, v in vars(args).items() if k != "list" and v}
        if other_args:
            logger.error("Cannot use other arguments with -l/--list option.")
            exit(1)

        logger.info("Available voices:")
        ShowVoiceList.print(args.list)

        exit(0)

    # input arguments
    input_file = args.input or args.positional_input
    if not input_file:
        logger.error("Input file name is required")
        exit(1)

    try:
        with open(input_file, "r", encoding="UTF-8") as f:
            f.read()
    except:
        logger.error(f"Cannot open {input_file}")
        exit(1)

    input_file = os.path.normpath(input_file)
    logger.info(f"Input file: {input_file}")

    # output arguments
    if args.output or args.positional_output:
        output_file = args.output or args.positional_output
        if os.path.basename(output_file) == "":
            logger.error("Output file name is not valid")
            exit(1)
        if not output_file.endswith(".mp3"):
            logger.error("Output file name must end with .mp3")
            exit(1)
    else:
        base_name = os.path.basename(input_file)
        file_name, _ = os.path.splitext(base_name)
        output_file = os.path.join(DEFAULT_OUTPUT_PATH, f"{file_name}.mp3")

    output_file = os.path.normpath(output_file)
    logger.info(f"Output file: {output_file}")

    # concurrencies arguments
    if args.concurrencies:
        thread_count = args.concurrencies
    else:
        thread_count = DEFAULT_THREADS

    logger.info("Starting to process input text file...")
    input_file_queue = TextQueue(input_file)

    queue_len = input_file_queue.get_length()
    if thread_count > queue_len:
        thread_count = queue_len

    create_output_folder(output_file)

    # generate voice
    logger.info(f"Starting to generate voice files...")
    speech_manager = SpeechManager(input_file_queue, output_file)
    speech_manager.multi_threading_generate(thread_count)
    output_filename_queue = speech_manager.get_output_filename_queue()
    error_output_filename_queue = speech_manager.get_error_output_filename_queue()

    # check if there are any error files
    if not error_output_filename_queue.empty():
        error_output_files: List[str] = []
        while not error_output_filename_queue.empty():
            error_output_files.append(error_output_filename_queue.get())
        error_output_files.sort(key=extract_number)

        
        for file in error_output_files:
            file = os.path.basename(file)
            logger.error(f"Generation failed for file {file}")

        if args.merge:
            logger.error("Cannot merge files due to generation errors.")

        exit(1)

    # merge arguments
    if args.merge:
        output_files: List[str] = []
        while not output_filename_queue.empty():
            output_files.append(output_filename_queue.get())
        output_files.sort(key=extract_number)

        logger.info(f"Merging {len(output_files)} files...")
        result = MergeVoiceFiles.merge(output_files, output_file)

        if result:
            logger.error(f"Error merging files:\n{result}")

            if os.path.exists(output_file):
                os.remove(output_file)

            exit(1)
            
    logger.info(f"Successfully generated voice files.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        exit(1)