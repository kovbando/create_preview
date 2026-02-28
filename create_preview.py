import os
from PIL import Image
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm
import signal
import sys

import argparse
import yaml

## ffmpeg command for rendering the video afterwards: ffmpeg -framerate 20 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 30 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
## ffmpeg -framerate 20 -i ./preview/frame_%04d.jpg -vf "scale=1920:-2" -c:v h264_nvenc -preset p1 -rc:v vbr -cq 30 -b:v 5M -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4


def load_images_from_folder(folder):
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])


class PreviewCreator:
    folders = []

    def __init__(self,
                 topics,
                 output_path,
                 cols,
                 rows,
                 image_width,
                 image_height):

        # check for valid topic folders
        for path in topics:
            if not os.path.isdir(path):
                print(f'No directory at {path}.')
            else:
                self.folders.append(path)

        # create output folder if it doesn't exist
        if os.path.isdir(output_path) and os.listdir(output_path):
            print('Error: output path is a non-empty folder.')
            exit()
        os.makedirs(output_path, exist_ok=True)
        self.output_path = output_path

        # calculate grid dimensions
        if cols and rows:
            self.cols = cols
            self.rows = rows
        else:
            if cols and not rows:
                self.cols = cols
                self.rows = (len(self.folders + 1)) // cols
            else:
                self.rows = rows
                self.cols = (len(self.folders + 1)) // rows

        self.image_size = (image_width, image_height)

    def create_grid_frame_and_save(self, index, folders_images, progress_queue):
        try:
            image_paths = [folder[index] for folder in folders_images]
            images = [Image.open(p).resize(self.image_size) for p in image_paths]

            grid_width = self.image_size[0] * self.cols
            grid_height = self.image_size[1] * self.rows
            grid_image = Image.new('RGB', (grid_width, grid_height))

            for idx, img in enumerate(images):
                row = idx // self.cols
                col = idx % self.cols
                position = (col * self.image_size[0], row * self.image_size[1])
                grid_image.paste(img, position)

            output_path = os.path.join(self.output_path, f"frame_{index:04d}.jpg")
            grid_image.save(output_path, quality=95)
        except Exception as e:
            print(f"Error on frame {index}: {e}", flush=True)
        finally:
            progress_queue.put(1)

    def unite_images(self):
        def handle_interrupt(sig, frame):
            print("\nInterrupt received, shutting down...", flush=True)
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_interrupt)

        print("Loading image paths...", flush=True)
        folders_images = [load_images_from_folder(folder) for folder in self.folders]
        frame_count = min(len(images) for images in folders_images)

        print(f"Starting frame generation for {frame_count} frames...", flush=True)
        args = list(range(frame_count))

        with Manager() as manager:
            progress_queue = manager.Queue()
            with Pool(processes=cpu_count()) as pool:
                for i in args:
                    pool.apply_async(self.create_grid_frame_and_save,
                                     args=(i, folders_images, progress_queue))

                try:
                    with tqdm(total=frame_count) as pbar:
                        completed = 0
                        while completed < frame_count:
                            progress_queue.get()
                            completed += 1
                            pbar.update(1)
                except KeyboardInterrupt:
                    print("\nKeyboardInterrupt received, terminating pool...", flush=True)
                    pool.terminate()
                    pool.join()
                    sys.exit(1)

        print(f"Saved {frame_count} frames to {self.output_path}/", flush=True)


def load_config_file(config_path):
    VALID_CONFIG_OPTIONS = {
            'topics': list,
            'output_dir': str,
            'cols': int,
            'rows': int,
            'image_width': int,
            'image_height': int,
        'source_fps': (int, float),
    }

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    # validate keys
    invalid_keys = set(config) - VALID_CONFIG_OPTIONS.keys()
    if invalid_keys:
        raise ValueError(f"Invalid config keys: {', '.join(invalid_keys)}. "
                         f"Valid keys are: {', '.join(sorted(VALID_CONFIG_OPTIONS.keys()))}")

    # validate types
    for key, expected_type in VALID_CONFIG_OPTIONS.items():
        if key in config and not isinstance(config[key], expected_type if isinstance(expected_type, tuple) else expected_type):
            if isinstance(expected_type, tuple):
                expected_names = ', '.join(t.__name__ for t in expected_type)
            else:
                expected_names = expected_type.__name__
            raise TypeError(f"Invalid type for '{key}': expected {expected_names}, got {type(config[key]).__name__}")

    return config


if __name__ == '__main__':
    # dedicated parser for config file so help shows full option list
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument('--config',
                               type=str, default='./topics.yaml',
                               help='Path to config file')

    # main parser inherits --config and handles help text
    parser = argparse.ArgumentParser(
        description='Sreates a collage of synchronized pictures from different output from ros2 bag export image.',
        parents=[config_parser]
    )

    # parse config path without triggering help prematurely
    args_config, remaining_argv = config_parser.parse_known_args()

    # load config file if it exists
    config_options = {}
    if os.path.exists(args_config.config):
        config_options = load_config_file(args_config.config)

    # parse remaining arguments
    parser.add_argument('-o', '--output_dir',
                        type=str, default='./preview',
                        help='Path to the output folder')
    parser.add_argument('-c', '--cols',
                        type=int,
                        help='Number of columns in collage')
    parser.add_argument('-r', '--rows',
                        type=int,
                        help='Number of rows in collage')
    parser.add_argument('-iw', '--image_width',
                        type=int, default=1920,
                        help='Input image width')
    parser.add_argument('-ih', '--image_height',
                        type=int, default=1080,
                        help='Input image height')
    parser.add_argument('-t', '--topics',
                        nargs='+',
                        help='Input topic (folder) names')

    # override defaults with config file options
    parser.set_defaults(**config_options)

    # TODO verbose/silent

    args = parser.parse_args(remaining_argv)

    # fill in any values missing from CLI with config defaults
    for key, value in config_options.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)

    args.config = args_config.config

    # Check if topics were provided either via config or command line
    if not args.topics:
        parser.error("the following arguments are required: -t/--topics (must be provided via config file or command line)")

    preview_creator = PreviewCreator(args.topics,
                                     os.path.realpath(args.output_dir),
                                     getattr(args, 'cols', None),
                                     getattr(args, 'rows', None),
                                     getattr(args, 'image_width', None),
                                     getattr(args, 'image_height', None),
                                     )
    preview_creator.unite_images()
