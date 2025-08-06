import os
from PIL import Image
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm
import signal
import sys

import argparse

## ffmpeg command for rendering the video afterwards: ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 30 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
## ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v h264_nvenc -preset p1 -rc:v vbr -cq 30 -b:v 5M -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4

IMAGE_SIZE = (1920, 1200)  # input image size
GRID_COLS = 2


def parse_config_file(config):
    folders = []

    try:
        with open(config, 'r') as file:
            for line in file:
                # Strip whitespace and newline characters
                path = line.strip()
                if path:  # Skip empty lines
                    if not os.path.isdir(path):
                        print(f'No directory at {path}.')
                    else:
                        folders.append(path)
    except FileNotFoundError:
        print(f"Error: The file '{config}' was not found.")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")

    return folders


def load_images_from_folder(folder):
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])


def create_grid_frame_and_save(index, folders_images, grid_rows, progress_queue, output):
    try:
        image_paths = [folder[index] for folder in folders_images]
        images = [Image.open(p).resize(IMAGE_SIZE) for p in image_paths]

        grid_width = IMAGE_SIZE[0] * GRID_COLS
        grid_height = IMAGE_SIZE[1] * grid_rows
        grid_image = Image.new('RGB', (grid_width, grid_height))

        for idx, img in enumerate(images):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            position = (col * IMAGE_SIZE[0], row * IMAGE_SIZE[1])
            grid_image.paste(img, position)

        output_path = os.path.join(output, f"frame_{index:04d}.jpg")
        grid_image.save(output_path, quality=95)
    except Exception as e:
        print(f"Error on frame {index}: {e}", flush=True)
    finally:
        progress_queue.put(1)


def unite_images(config, output):
    os.makedirs(output, exist_ok=True)

    folders = parse_config_file(config)
    grid_rows = (len(folders) + 1) // GRID_COLS

    def handle_interrupt(sig, frame):
        print("\nInterrupt received, shutting down...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    print("Loading image paths...", flush=True)
    folders_images = [load_images_from_folder(folder) for folder in folders]
    frame_count = min(len(images) for images in folders_images)

    print(f"Starting frame generation for {frame_count} frames...", flush=True)
    args = list(range(frame_count))

    with Manager() as manager:
        progress_queue = manager.Queue()
        with Pool(processes=cpu_count()) as pool:
            for i in args:
                pool.apply_async(create_grid_frame_and_save, args=(i, folders_images, grid_rows, progress_queue, output))

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

    print(f"Saved {frame_count} frames to {output}/", flush=True)


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Sreates a collage of synchronized pictures from different output from ros2 bag export image.')
    parser.add_argument('-c', '--config',
                        type=str,
                        required=True,
                        help='Path to the config file containing paths to folders in the order their contents should appear in collages')
    parser.add_argument('-o', '--output_dir',
                        type=str, required=False, default='.',
                        help='Path to the output folder')

    args = parser.parse_args()
    unite_images(args.config, args.output_dir)
