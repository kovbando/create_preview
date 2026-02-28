# This is the speedup branch!!!
TODO: make and test better optimized FFMPEG commmands
TODO: update readme to reflect all the small changes in the speedup branch
TODO: merge speedup branch
This branch has an updated process pooling logic, and performs way better than the main brancch, but needs more testing!

# create_preview
Python script to create a collage of synchronized or unsynchronized pictures output from ros2 bag export images. These scripts will not create the actual video, you will need to run ffmpeg manually for that, but there are some guidelines on how to do that.\
**Please read the Sync logic section before running the script.**

# Dependencies
The only non-python dependency is FFMPEG, which is not needed if you only want pictures as the output. You probably already have it on your system, but if not, just run
```
sudo apt install ffmpeg
```
Preferably use a python virtual environment, and install dependencies via pip
```
pip install -r requirements.txt
```
# Sync logic
There is two python scripts, that do the same thing, and use the same options, but with different synchronizaton logic.\
`create_preview.py` is the simpler, It reads all the files from all the input topic folders, and puts them side-by-side. The reesultt will be as many combined images as many files there are in the topic containing the *least* amount of pictures. This logic kind of crude, and does *not* take into account any kind of timestamping.\
`synced_previews.py` has a mopre advanced sync logic. It reads all the files, and it needs to have an FPS configured. It will parse the filenames of every file, interpret them as a nanosecond level UNIX-timestamp. Then, based on the timestamps and FPS it puts the closest in time pictures in the collage. This way the time  sync between all the selected topics are kept, based on the timestamp. If there is a missing frame, it will be filled by the closest-in-time frame, so the output will always have all the cameras filled. 

# Usage
The script can be run with various options described by
```
python create_preview.py -h
```
You can configure all the accepted parameters in a yaml file. For an example look at `configuration.yaml`. After editing the yaml file run the program with:
```
python3 create_preview.py --config configuration.yaml
```

The following options can be specified in a yaml config file (given in the option --config):
```
topics: list,
output_dir: str,
cols: int,
rows: int,
image_width: int,
image_height: int,
source_fps: float,
```

## Turning images to video
After running the script, you will have all the images, but still no video. To turn the images into a video file, use FFMPEG. There are two example commands, that produce good results.\
If you want to use CPU for encoding:
```
ffmpeg -framerate 20 -i ./preview/frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 20 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
```
If you have an nvidia GPU and want to accelerate the encoding process:
```
ffmpeg -framerate 20 -i ./output_frames/frame_%04d.jpg -vf "scale=1920:-2" -c:v hevc_nvenc -preset p6 -rc vbr -cq 20 preview.mp4
ffmpeg -framerate 20 -i ./output_frames/frame_%04d.jpg -c:v hevc_nvenc -preset p6 -rc vbr -cq 20 preview.mp4
```
