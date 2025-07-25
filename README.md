# create_preview
Python script to create a 3x2 collage of synchronized pictures output from ros2 bag export images.
# Dependencies
The only nan-python dependency is FFMPEG. You probably already have it on your system, but if not, just run\
`sudo apt install ffmpeg`\
Preferably use a python virtual environment, and install dependencies via pip\
`pip install -r requirements.txt`
# Usage
When you have all the pictures ready to be turned into a preview video, run "create_preview.py" with the `-c` option followed by the path to a file containing the folders to use the images from, in the order they should appear in the collage.\
All the merged images will be in a folder named "output_frames" in the folder specified in `-o`.
## Turning images to video
After running the script, you will have all the images, but still no video. To turn the images into a video file, use FFMPEG. There are two example commands, that produce good results.\
If you want to use CPU for encoding:\
`ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 30 -threads 8 -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4`\
If you have an nvidia GPU and want to accelerate the encoding process:\
`ffmpeg -framerate 12 -i frame_%04d.jpg -vf "scale=1920:-2" -c:v h264_nvenc -preset p1 -rc:v vbr -cq 30 -b:v 5M -max_muxing_queue_size 1024 -bufsize 256M -rtbufsize 256M output.mp4`
# TODOs
Handle input and output folders from passed arguments, so aneble integration with other scripts.\
Add the FFMPEG commend to the end of the script, so it will run automatically.
