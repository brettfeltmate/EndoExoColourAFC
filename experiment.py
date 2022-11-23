# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import klibs
import numpy as np
from klibs import P
from klibs.KLConstants import TK_MS, RC_COLORSELECT
from klibs.KLGraphics.colorspaces import const_lum
from klibs.KLUtilities import deg_to_px, now, mouse_pos, hide_mouse_cursor, show_mouse_cursor
from klibs.KLUserInterface import ui_request, any_key
from klibs.KLCommunication import message
from klibs.KLGraphics import fill, blit, flip
from klibs.KLGraphics import KLDraw as kld
from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLAudio import AudioClip

import aggdraw  # For drawing mask cells in a single texture
from PIL import Image
import random
import math

WHITE = (255, 255, 255, 255)
PRE = "pre_cue"
CUE = "cue"
POST = 'post_cue'
SHORT = 'short'
LONG = 'long'
TARGET = 'target'
WHEEL = 'wheel'
CURSOR = 'cursor'
MASK = 'mask'
VALID = 'valid'
INVALID_SHORT = 'invalid_short'
INVALID_LONG = 'invalid_long'
FIX = 'fixation'
CATCH = 'catch'

class EndoExoColourAFC(klibs.Experiment):

	def setup(self):

		#self.trial_factory = TrialFactory()

		self.target_duration = 100

		# Cue-Target Onset Asynchrony factor labels and their respective durations
		self.ctoa_map = {
			SHORT: {
				VALID: 400,
				INVALID_SHORT: 1000,
				INVALID_LONG: 1600
			},
			LONG: {
				VALID: 1600,
				INVALID_SHORT: 400,
				INVALID_LONG: 1000
			}
		}

		# Perceptual sizes of stimuli
		self.sizes = {
			CUE: deg_to_px(P.cue_size),
			TARGET: deg_to_px(P.target_size),
			WHEEL: [deg_to_px(P.wheel_size[0]), deg_to_px(P.wheel_size[1])],
			CURSOR: [deg_to_px(P.cursor_size[0]), deg_to_px(P.cursor_size[1])]  # diameter, thickness
		}

		# Font size of cue, which is a string of concatenated dashes
		self.txtm.add_style(CUE, font_size=self.sizes[CUE])

		# Stimulus objects
		self.stims = {
			LONG: message('----------------', style=CUE, location=P.screen_c, registration=5, blit_txt=False),
			SHORT: message('----', style=CUE, location=P.screen_c, registration=5, blit_txt=False),
			TARGET: kld.Rectangle(width=self.sizes[TARGET]),
			WHEEL: kld.ColorWheel(diameter=self.sizes[WHEEL][0], thickness=self.sizes[WHEEL][1], auto_draw=False),
			CURSOR: kld.Annulus(diameter=self.sizes[CURSOR][0], thickness=self.sizes[CURSOR][1], fill=WHITE),
			FIX: kld.FixationCross(size=self.sizes[TARGET], thickness=deg_to_px(0.1), fill=WHITE)
		}

		# Response collector object, uses colourwheel
		self.rc_wheel = ResponseCollector(uses=RC_COLORSELECT)
		self.rc_wheel.color_listener.color_response = True

		if P.run_practice_blocks:
			self.insert_practice_block(1, trial_counts=P.trials_per_practice_block, factor_mask={'catch_trial': [False]})

		self.say_welcome = True

	def block(self):
		if P.practicing:
			if self.say_welcome:
				fill()
				message(
					"Welcome to the task. \n Use the auditory warning signals to prepare for whichever time interval is indicated. \n Respond as quickly as possible, and pick the target colour to the best of your ability. \n Press any key to begin the experiment.",
					location=P.screen_c,
					registration=5, blit_txt=True)
				flip()
				self.say_welcome = False


			any_key()
		# anything you want them to see on first exp block
		elif P.block_number == 1:
			fill()
			message(
				"Practice is complete. If you have any questions, ask your experimenter. \n Press any key to begin "
				"the experiment.",
				location=P.screen_c, registration=5, blit_txt=True)
			flip()

			any_key()

		# anything for remaining blcoks
		else:
			fill()
			message("Take a break! You have finished a block of trials. \n To continue, click the mouse button.",
			        location=P.screen_c, registration=5,
			        blit_txt=True)
			flip()

			any_key()

	def setup_response_collector(self):
		# When to stop listening for responses
		self.rc_wheel.terminate_after = [P.discrimination_timeout, TK_MS]
		# What to present during response period (custom function defined at end of file)
		self.rc_wheel.display_callback = self.discrimination_callback

	def trial_prep(self):
		# Provide quarterly breaks during testing blocks
		if not P.practicing and P.trial_number > 1:
			if P.trial_number % (P.trials_per_block / 4) == 1:
				fill()
				message("Good job!\nTake a break!\nPress any key to continue...", location=P.screen_c, registration=5,
				        blit_txt=True)
				flip()

				any_key()
		# Given the cue presented (short, long),
		# and it's validity for this trial, extract the appropriate CTOA duration
		self.ctoa = self.ctoa_map[self.cue_value][self.cue_valid] if not self.catch_trial else 1600

		# Randomly select fixation - cue duration for trial
		self.fixation_duration = self.get_fixation_interval()

		# Compose alerting signal for trial
		self.trial_audio = self.get_trial_audio()
		self.base_volume = 0.1
		self.cue_volume = 0.2 if self.signal_intensity == 'hi' else self.base_volume

		# If a target is to be presented, establish & construct relevant visual assets
		if not self.catch_trial:
			# Post target visual mask
			self.stims[MASK] = self.generate_mask()

			# Spin the wheel and render
			self.stims[WHEEL].rotation = np.random.randint(0, 360)
			self.stims[WHEEL].render()

			# Randomly select colouring & paint target
			self.target_angle = np.random.randint(0, 360)
			self.target_rgb = self.stims[WHEEL].color_from_angle(self.target_angle)
			self.stims[TARGET].fill = self.target_rgb

			# Assign rendered wheel to RC, inform it of the target colour
			self.rc_wheel.color_listener.set_wheel(self.stims[WHEEL])
			self.rc_wheel.color_listener.set_target(self.stims[TARGET])

		# Define & register event sequence and timings
		events = []
		events.append([self.fixation_duration, 'play_alerting_signal'])
		events.append([events[-1][0] + P.cue_duration, 'stop_alerting_signal'])
		events.append([events[-1][0] + self.ctoa, 'target_on'])
		events.append([events[-1][0] + self.target_duration, 'mask_on'])
		events.append([events[-1][0] + P.mask_duration, 'response_period'])

		for e in events:
			self.evm.register_ticket([e[1], e[0]])

	def trial(self):
		hide_mouse_cursor()

		# Start audio
		self.trial_audio.play()

		# Present visual cue
		fill()
		blit(self.stims[self.cue_value], location=P.screen_c, registration=5)
		flip()

		# Wait to play alerting signal
		while self.evm.before('play_alerting_signal'):
			ui_request()  # Ensures experiment doesn't lock up machine

		# Play alerting signal (increase in volume on exogenously alerting trials)
		self.trial_audio.volume = self.cue_volume

		# Wait to stop
		while self.evm.before('stop_alerting_signal'):
			ui_request()

		# Revert alerting signal to baseline state
		self.trial_audio.volume = self.base_volume

		# Wait to present target
		while self.evm.before('target_on'):
			ui_request()

		# If a target is to be presented
		if not self.catch_trial:

			# Blit target to screen
			fill()
			blit(self.stims[TARGET], registration=5, location=P.screen_c)
			flip()

			while self.evm.before('mask_on'):
				ui_request()

			# Blit mask
			fill()
			blit(self.stims[MASK], registration=5, location=P.screen_c)
			flip()

			while self.evm.before('response_period'):
				ui_request()

			# Present colour wheel
			show_mouse_cursor()
			self.rc_wheel.collect()
			discrimination = self.rc_wheel.color_listener.response()

		# Log trial data
		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"fix_duration": self.fixation_duration,
			"target_duration": self.target_duration,
			"ctoa": self.ctoa,
			"cue_valid": CATCH if self.catch_trial else self.cue_valid,
			"signal_intensity": self.signal_intensity,
			"target_rgb": CATCH if self.catch_trial else self.target_rgb,
			"discrimination_rt": CATCH if self.catch_trial else discrimination.rt,
			"discrimination_error": CATCH if self.catch_trial else discrimination.value[0]
		}


	def trial_clean_up(self):
		self.rc_wheel.color_listener.reset()

		# Fix is probably a bad name, really it's just a visual signal that delineates trials
		fill()
		blit(self.stims[FIX], location=P.screen_c, registration=5)
		flip()

		ITI_start = now()

		while now() < ITI_start + (P.ITI / 1000):
			ui_request()

		self.trial_audio.stop()

		if P.practicing and P.trial_number == P.trials_per_practice_block:
			self.performance_check()

	def clean_up(self):
		pass

	# Presents colour selection wheel during response period
	def discrimination_callback(self):

		fill()
		blit(self.stims[WHEEL], location=P.screen_c, registration=5)
		blit(self.stims[CURSOR], location=mouse_pos(), registration=5)
		flip()


	# Composes audio track for trial
	def get_trial_audio(self):

		# Generate pre-cue noise signal
		fix_L = self.generate_noise(self.fixation_duration)
		fix_R = fix_L
		fix = np.c_[fix_L, fix_R]

		# Generate noise signals for both channels to serve as alerting signal
		alert_L = self.generate_noise(P.cue_duration)
		alert_R = self.generate_noise(P.cue_duration)
		alert = np.c_[alert_L, alert_R]

		# Compose post-alerting signal, ensuring duration sufficient to cover remainder of trial.
		post_duration = self.ctoa + P.target_duration + P.discrimination_timeout + P.ITI + 1000
		post_L = self.generate_noise(post_duration)
		post_R = post_L

		post = np.c_[post_L, post_R]

		clip = np.r_[fix, alert, post]

		return AudioClip(clip=clip, volume=0.1)

	# Generates values which are converted to audio clip
	def generate_noise(self, duration):
		max_int = 2 ** 16 / 2 - 1  # 32767, which is the max/min value for a signed 16-bit int
		dtype = np.int16  # Default audio format for SDL_Mixer is signed 16-bit integer
		sample_rate = 44100 / 2  # sample rate for each channel is 22050 kHz, so 44100 total.
		clip_length = int((duration / 1000.0) * sample_rate) * 2


		arr = np.random.uniform(low=-1.0, high=1.0, size=clip_length) * max_int

		return arr.astype(dtype)

	# Randomly samples fix-cue duration from non-decaying time function
	def get_fixation_interval(self):
		max_f, min_f, mean_f = P.fixation_max, P.fixation_min, P.fixation_mean

		interval = random.expovariate(1.0 / float(mean_f - min_f)) + min_f
		while interval > max_f:
			interval = random.expovariate(1.0 / float(mean_f - min_f)) + min_f

		return interval

	# Generates mask of randomly coloured squares, presented post-target
	def generate_mask(self):
		cells = 16
		# Set mask size
		canvas_size = self.sizes[TARGET]
		# Set cell size
		cell_size = int(canvas_size / math.sqrt(cells))  # Mask comprised of 4 smaller cells arranged 2x2
		# Each cell has a black outline
		cell_outline_width = deg_to_px(.05)

		# Initialize canvas to be painted w/ mask cells
		canvas = Image.new('RGBA', [canvas_size, canvas_size], (0, 0, 0, 0))

		surface = aggdraw.Draw(canvas)

		# Initialize pen to draw cell outlines
		transparent_pen = aggdraw.Pen((0, 0, 0), cell_outline_width)

		count = int(math.sqrt(cells))

		# Generate cells, arranged in 4x4 array
		for row in range(count):
			for col in range(count):
				# Randomly select colour for each cell
				cell_colour = const_lum[random.randrange(0, 360)]
				# Brush to apply colour
				colour_brush = aggdraw.Brush(tuple(cell_colour[:3]))
				# Determine cell boundary coords
				top_left = (row * cell_size, col * cell_size)
				bottom_right = ((row + 1) * cell_size, (col + 1) * cell_size)
				# Create cell
				surface.rectangle(
					(top_left[0], top_left[1], bottom_right[0], bottom_right[1]),
					transparent_pen,
					colour_brush)
		# Apply cells to mask
		surface.flush()

		return np.asarray(canvas)

	def performance_check(self):
		print("Performance check")
		print("Prior target duration: {}".format(self.target_duration))

		#  get mean error
		error = self.get_error()
		print('mean error = {}'.format(error))

		more_practice_needed = True

		# If target duration at max, and error is still too high, abort experiment
		if self.target_duration == 150:
			if error > 50:
				message("Please inform the researcher that you suck.", registration=5, location=P.screen_c, flip_screen=True)
				any_key()
				quit()

			else:
				more_practice_needed = False

		# If target duration at min, check for poor performance (upping duration if so), otherwise proceed with testing.
		elif self.target_duration == 33:
			if error > 50:
				self.target_duration = 67
			more_practice_needed = False

		# Next two higher clauses refer to middling durations,
		# If above/below performance thresholds, adjust duration accordingly
		elif self.target_duration == 100:
			if error > 50:
				self.target_duration = 150

			elif error < 30:
				self.target_duration = 67

			else:
				more_practice_needed = False

		else:  # target duration here == 67ms
			if error < 30:
				self.target_duration = 33
			elif error > 50:
				self.target_duration = 100
				more_practice_needed = False
			else:
				more_practice_needed = False

		print("Adjusted target duration: {}".format(self.target_duration))

		if more_practice_needed:
			self.trial_factory.insert_block(
				block_num=P.block_number + 1,
				practice=True,
				trial_count=P.trials_per_practice_block,
				factor_mask={'catch_trial': [False]}
			)

	def get_error(self):
		try:
			val = self.db.query(
				"SELECT discrimination_error FROM trials WHERE participant_id = {0} AND block_num = {1}".format(
					P.participant_id, P.block_number), fetch_all=True)

			vals = []
			for v in val:
				try:
					vals.append(float(v[0]))
				except ValueError:
					pass


			return np.mean(np.abs(vals))
		except IndexError:
			return 0
