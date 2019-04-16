import contextlib
with contextlib.redirect_stdout(None):
	from moviepy.editor import VideoClip, VideoFileClip, concatenate_videoclips
	from moviepy.audio.AudioClip import AudioArrayClip
from librosa.effects import time_stretch
from librosa.effects import pitch_shift
from librosa.core import to_mono
import numpy as np
import argparse
import os

class Section:
	def __init__(self, start, stop):
		self.start = start
		self.stop = stop

def cut_silence(video_clip, margin, cutoff, step):
	# Splits up clip audio based on step
	cut = lambda i: video_clip.audio.subclip(i, i + step).to_soundarray(fps=22000)

	# Get audio of a clip
	volume = lambda array: np.sqrt(((1.0 * array)**2).mean())

	# Get audio range of a clip
	volume_range = lambda array: np.amax(array) - np.amin(array)

	# Get volume throughout clip, max volume, and compute cutoff volume
	times = np.arange(0, clip.duration - step, step)
	volumes = [volume(cut(i)) for i in times]
	max_volume = np.amax(volumes)
	cutoff_volume = cutoff * volume_range(volumes)

	# Make list of sections to keep based on cutoff volume
	sections = []
	start = -1
	for t, v in zip(times, volumes):
		if start == -1 and v > cutoff_volume:
			start = t - margin
		if start != -1 and v < cutoff_volume:
			sections.append(Section(start, t + margin))
			start = -1

	if len(sections) > 1:
		# Ensure sections are within bounds
		if sections[0].start < 0:
			sections[0].start = 0
		if sections[-1].stop > clip.duration:
			sections[-1].stop = clip.duration

		# Ensure no overlap
		i = 0
		while i < (len(sections) - 1):
			if sections[i].stop >= sections[i+1].start:
				sections[i].stop = sections[i+1].stop
				sections.pop(i+1)
			else:
				i+=1
				
    # Concatenate results and fix volume
	video_clips = [clip.subclip(s.start, s.stop) for s in sections]
	if len(video_clips) == 0:
		video_clips = [clip]
	return concatenate_videoclips(video_clips).volumex(0.9/max_volume)

def speed_up(video_clip, speed):
	rate = 44100
	
	# Speed up video
	video_clip = video_clip.speedx(speed)

	# Determine pitch shift from speed
	shift = (1 - speed if speed >= 1 else (1 / speed) - 1) * 12

	# Fix audio pitch
	audio = video_clip.audio.to_soundarray(fps=rate).transpose()
	for i, channel in enumerate(audio):
		audio[i] = pitch_shift(channel, rate, shift)
	audio = audio.transpose()
	
	video_clip.audio = AudioArrayClip(audio, fps=rate)

	return video_clip
	
# Arguments
parser = argparse.ArgumentParser(description="Remove silent sections of videos, and change the speed of what's left.")
parser.add_argument('--input_path', type=str, help='The relative path to the file (or folder containing multiple files) which will be edited.')
parser.add_argument('--speed', type=float, help='The speed of the video will be multiplied by this. Default = 1.5.', default=1.5)
parser.add_argument('--cutoff', type=float, help='If the volume is less than this value multiplied by the max volume, the clip gets cut. Default = 0.2.', default=0.20)
parser.add_argument('--margin', type=float, help='A margin of this many seconds is subtracted from silent portions. Default = 0.1.', default=0.1)
parser.add_argument('--step', type=float, help='The increment (in seconds) at which volume is sampled. Default = 0.1.', default=0.1)
parser.add_argument('--fps', type=int, help='The FPS of the exported video. Default = 30.', default=30)

args = parser.parse_args()

input_path = args.input_path
speed = args.speed
cutoff = args.cutoff
margin = args.margin
step = args.step
fps = args.fps

# Gather files
files = []
if os.path.isdir(input_path):
	for f in os.listdir(input_path):
		if os.path.isfile(os.path.join(input_path, f)):
			files.append(os.path.join(input_path, f))
elif os.path.isfile(input_path):
	files.append(input_path)
else:
	print("Could not identify input path.")

# Edit files
for f in files:
	with VideoFileClip(f) as clip:
		duration = clip.duration
		print("Initial duration: %.2f seconds." % duration)
		
		clip = cut_silence(clip, margin, cutoff, step)
		print("Removed %.2f seconds." % (duration - clip.duration))
		
		clip = speed_up(clip, speed)
		print("Compressed to %.2f seconds." % clip.duration)
		
		# Save files to output folder
		if not os.path.exists("output"):
			os.makedirs("output")
		clip.write_videofile('output/%s' % f, fps=fps)