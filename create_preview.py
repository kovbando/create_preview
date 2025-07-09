import os
from PIL import Image
import numpy as np
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm
import signal
import sys

## ffmpeg command for rendering the video afterwards: ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 30 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
## ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v h264_nvenc -preset p1 -rc:v vbr -cq 30 -b:v 5M -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4

FOLDERS = [
    '/mnt/s/cutbag/image_1',# top-left
    '/mnt/s/cutbag/image_2',# top-right
    '/mnt/s/cutbag/image_0',# middle-left
    '/mnt/s/cutbag/image_5',# middle-right
    '/mnt/s/cutbag/image_3',# bottom-left
    '/mnt/s/cutbag/image_4',# bottom-right
]

OUTPUT_FOLDER = 'output_frames'
IMAGE_SIZE = (1920, 1200)  # input image size
GRID_ROWS = 3
GRID_COLS = 2

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def load_images_from_folder(folder):
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

def create_grid_frame_and_save(index, folders_images, progress_queue):
    try:
        image_paths = [folder[index] for folder in folders_images]
        images = [Image.open(p).resize(IMAGE_SIZE) for p in image_paths]

        grid_width = IMAGE_SIZE[0] * GRID_COLS
        grid_height = IMAGE_SIZE[1] * GRID_ROWS
        grid_image = Image.new('RGB', (grid_width, grid_height))

        for idx, img in enumerate(images):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            position = (col * IMAGE_SIZE[0], row * IMAGE_SIZE[1])
            grid_image.paste(img, position)

        output_path = os.path.join(OUTPUT_FOLDER, f"frame_{index:04d}.jpg")
        grid_image.save(output_path, quality=95)
    except Exception as e:
        print(f"Error on frame {index}: {e}", flush=True)
    finally:
        progress_queue.put(1)

def main():
    def handle_interrupt(sig, frame):
        print("\nInterrupt received, shutting down...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    print("Loading image paths...", flush=True)
    folders_images = [load_images_from_folder(folder) for folder in FOLDERS]
    frame_count = min(len(images) for images in folders_images)

    print(f"Starting frame generation for {frame_count} frames...", flush=True)
    args = list(range(frame_count))

    with Manager() as manager:
        progress_queue = manager.Queue()
        with Pool(processes=cpu_count()) as pool:
            for i in args:
                pool.apply_async(create_grid_frame_and_save, args=(i, folders_images, progress_queue))

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

    print(f"Saved {frame_count} frames to {OUTPUT_FOLDER}/", flush=True)

if __name__ == '__main__':
    main()
