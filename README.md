# create_preview
Python script to create a collage of synchronized pictures output from ros2 bag export images.

# Dependencies
The only nan-python dependency is FFMPEG. You probably already have it on your system, but if not, just run\
```
sudo apt install ffmpeg
```
Preferably use a python virtual environment, and install dependencies via pip\
```
pip install -r requirements.txt
```
# Usage
The script can be run with possible options described by
```
python3 create_preview.py -h
```
You can configure all the accepted parameters in a yaml file. For example look at `configuration.yaml`. After editing the yaml file run the program with:
```
python3 create_preview.py -c configuration.yaml
```

The following options can be specified in a yaml config file (given in the option --config):
```
topics: list,
output_dir: str,
cols: int,
rows: int,
image_width: int,
image_height: int,
```

## Turning images to video
After running the script, you will have all the images, but still no video. To turn the images into a video file, use FFMPEG. There are two example commands, that produce good results.\
If you want to use CPU for encoding:
```
ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 30 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
```
If you have an nvidia GPU and want to accelerate the encoding process:
```
ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v h264_nvenc -preset p1 -rc:v vbr -cq 30 -b:v 5M -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4
```