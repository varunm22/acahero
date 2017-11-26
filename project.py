#pset6.py

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *
from common.clock import *
from common.synth import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
# from common.kivyparticle import ParticleSystem
from kivy.config import Config

from random import randint, random
import numpy as np
import bisect
from functools import partial

from pitch_detector import *
from display import *

Config.set('graphics', 'fullscreen', 'auto')
Config.write()

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        # Set terminal color to white
        Window.clearcolor = (.8, .8, .8, .8) 

        self.timelabel = topright_label((Window.width * 0.4, Window.height * 0.35))
        self.add_widget(self.timelabel)

        self.scorelabel = topright_label((Window.width * 0.4, Window.height * 0.4))
        self.add_widget(self.scorelabel)

        self.streaklabel = center_label()
        self.add_widget(self.streaklabel)

        self.name = name_label()
        self.add_widget(self.name)

        self.pitchlabel = center_label()
        self.add_widget(self.pitchlabel)

        self.clock = Clock()
        self.clock.stop()
        self.gametime = -SCREEN_TIME
        self.gameon = False

        self.old_cursor_y = 1
        self.filter_rate = 0.4

        self.audio = AudioController("songs/wdik/wdik-All.wav", "songs/wdik/wdik-Tenor.wav", receive_audio_func=self.receive_audio)

        # Display user's cursor
        # self.cursorcol = Color(1,0,0)
        self.cursorcol = Color(.6,.6,.6)
        self.canvas.add(self.cursorcol)
        self.user = Triangle(points=[NOW_PIXEL-60, -30, NOW_PIXEL-60, 30, NOW_PIXEL, 0])
        # self.user = Triangle(points=[NOW_PIXEL-30, -10, NOW_PIXEL-30, 10, NOW_PIXEL+10, 0])
        self.canvas.add(self.user)

        # Add particle system, which is used in BeatMatchDisplay when user sings the correct pitch.
        self.ps = ParticleSystem('particle/particle.pex')
        self.add_widget(self.ps)

        self.lanes, gem_data, barlineData, self.beatData = SongData().read_data('songs/wdik/Tenor.txt', 'songs/wdik/barlines.txt', 'songs/wdik/beats.txt')
        self.healthbar = HealthBar()
        self.display = BeatMatchDisplay(self.lanes, gem_data, barlineData, self.beatData, self.ps)
        self.canvas.add(self.healthbar)
        self.canvas.add(self.display)

        self.player = Player(self.lanes, gem_data, self.display, self.audio, PitchDetector())

        # Display screen when starting game. 
        self.name.text = "[color=000000][b]ACAHERO[/b]"
        self.scorelabel.text = "[color=000000]Score: 0"
        self.timelabel.text = "Time: %.2f" % self.gametime
        self.streaklabel.text = "[color=000000][b]keys[/b]\n[i]p:[/i] [size=30]play | pause[/size]\n[i]12345:[/i] [size=30]gems[/size]"
        # self.pitchlabel.text = 'correct pitch: %f \n current pitch: %f \n correct lane: %f' % (self.player.correct_pitch, self.player.cur_pitch, self.player.cor_lane)

        self.display.draw_objects()

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.toggle()

    def toggle(self):
        self.gameon = not self.gameon
        self.audio.toggle()
        self.display.toggle()
        self.clock.toggle()
        Window.clearcolor = (1, 1, 1, 1) if self.gameon else (.8,.8,.8,.8)

    def endgame(self):
        self.toggle()
        self.timelabel.text = "Game Ended"
        self.streaklabel.text = 'Final Percentage: {}%'.format(round(self.player.get_score()*100.))

    def get_cursor_y(self):
        bottom_pitch = self.lanes[-2] - 12
        top_pitch = self.lanes[1] + 12
        if self.player.cur_pitch < bottom_pitch:
            return 0
        if self.player.cur_pitch >= top_pitch:
            return GAME_HEIGHT
        bottom_i = -1
        top_i = len(self.lanes)
        # find the two lanes that the pitch is between
        for i in range(len(self.lanes)):
            if self.player.cur_pitch < self.lanes[i]:
                top_i = i
                top_pitch = self.lanes[i]
                break
            else:
                bottom_i = i
                bottom_pitch = self.lanes[i]
        # snap to the nearest 1/3
        frac = round((self.player.cur_pitch-bottom_pitch)/(top_pitch-bottom_pitch)*5)/5.
        bottom_pos = lane_to_y_pos(bottom_i, len(self.lanes))
        top_pos = lane_to_y_pos(top_i, len(self.lanes))
        # return the y position that the cursor should be at
        return bottom_pos + frac*(top_pos-bottom_pos)

    def on_update(self) :
        # Only update when gameplay is on
        if self.gameon:
            curr_gametime = self.clock.get_time() - SCREEN_TIME
            dt = curr_gametime - self.gametime
            self.gametime = curr_gametime

            self.timelabel.text = "Time: %.2f" % self.gametime
            self.scorelabel.text = 'Score: {:4.2f}'.format(self.player.get_score())
            # self.pitchlabel.text = 'correct pitch: %f \n current pitch: %f' % (self.player.correct_pitch, self.player.cur_pitch)

            # Only display a streak if there is a current streak > 1
            self.streaklabel.text = '[color=CFB53B]{}X Streak'.format(self.player.get_streak()) if self.player.get_streak() > 1 else ''

            self.audio.on_update(self.gametime)
            self.display.on_update(self.gametime, dt)
            self.player.on_update(self.gametime)
            self.healthbar.on_update(self.player.get_score())

            # 3,2,1 Start game countdown
            if -3 < self.gametime < -2:
                self.streaklabel.text = '3'
            elif -2 < self.gametime < -1:
                self.streaklabel.text = '2'
            elif -1 < self.gametime < 0:
                self.streaklabel.text = '1'

            # End game
            if self.gametime > self.beatData[-1]+2:
                self.endgame()
        
        if self.player.cur_pitch == 0:
            # self.cursorcol.r = 1
            # self.cursorcol.g = 0
            self.cursorcol.r = 0.6
            self.cursorcol.g = 0.6
            self.cursorcol.b = 0.6
        else:
            # self.cursorcol.r = 0
            # self.cursorcol.g = 1
            self.cursorcol.r = 0
            self.cursorcol.g = 0
            self.cursorcol.b = 0
            # lane = self.lanes.index(np.round(self.player.cur_pitch))
            # y = lane_to_y_pos(lane, self.num_lanes)
        # self.ps.emitter_y = y
        y = self.get_cursor_y()
        # Update the user's cursor
        if y < GAME_HEIGHT:
            cursor_y = self.filter_rate*y + (1-self.filter_rate)*self.old_cursor_y
            self.old_cursor_y = cursor_y
            self.user.points = [NOW_PIXEL-60, cursor_y-30, NOW_PIXEL-60, cursor_y+30, NOW_PIXEL, cursor_y]
            # self.user.points = [NOW_PIXEL-30, y-10, NOW_PIXEL-30, y+10, NOW_PIXEL+10, y]

    def receive_audio(self, frames, num_channels) :
        # handle 1 or 2 channel input.
        # if input is stereo, mono will pick left or right channel. This is used
        # for input processing that must receive only one channel of audio (RMS, pitch, onset)
        if num_channels == 2:
            mono = frames[0::2] # pick left or right channel
        else:
            mono = frames

        # Microphone volume level, take RMS, convert to dB.
        # display on meter and graph
        rms = np.sqrt(np.mean(mono ** 2))
        rms = np.clip(rms, 1e-10, 1) # don't want log(0)
        db = 20 * np.log10(rms)      # convert from amplitude to decibels 

        # pitch detection: get pitch and display on meter and graph
        self.player.receive_audio(mono)

# creates the Audio control
# creates a song and loads it with solo and bg audio tracks
# creates snippets for audio sound fx
class AudioController(object):
    def __init__(self, bg_path, solo_path, receive_audio_func):
        super(AudioController, self).__init__()
        self.audio = Audio(2, input_func=receive_audio_func)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        self.wave_gen_bg = WaveGenerator(WaveFile(bg_path))
        self.wave_gen_solo = WaveGenerator(WaveFile(solo_path))
        self.wave_gen_bg.pause()
        self.wave_gen_solo.pause()

    def start_music(self):
        self.wave_gen_solo.set_gain(0.8)
        self.wave_gen_bg.set_gain(0.7)

        self.mixer.add(self.wave_gen_solo)
        self.mixer.add(self.wave_gen_bg)

    # start / stop the song
    def toggle(self):
        self.wave_gen_bg.play_toggle()
        self.wave_gen_solo.play_toggle()

    # needed to update audio
    def on_update(self, gametime):
        self.audio.on_update()

        if gametime >= 0.:
            self.start_music()

# holds data for gems and barlines.
class SongData(object):
    def __init__(self):
        super(SongData, self).__init__()
        self.GemDict = {}
        self.BarlineList = []
        self.Lanes = []
        self.BeatList = []

    # read the gems and song data. You may want to add a secondary filepath
    # argument if your barline data is stored in a different txt file.
    def read_data(self, gemFile, barlineFile, beatFile):
    # TODO: figure out how gem and barline data should be accessed...
        gems = open(gemFile, 'r').readlines()
        barlines = open(barlineFile, 'r').readlines()
        beats = open(beatFile, 'r').readlines()

        for i, gem in enumerate(gems):
            if (i==0):
                self.Lanes = [int(x) for x in gem.split(" ")]
                continue

            time, duration, lane, lyric = gem.split("\t")
            lyric = lyric.strip()
            if lyric == "None":
                lyric = "-"
            self.GemDict.setdefault(int(lane), []).append((float(time), float(duration), lyric))

        for barline in barlines:
            time = barline.strip()
            self.BarlineList.append(float(time))

        for beat in beats:
            time = beat.strip()
            self.BeatList.append(float(time))

        return self.Lanes, self.GemDict, self.BarlineList, self.BeatList


# Handles game logic and keeps score.
# Controls the display and the audio
class Player(object):
    def __init__(self, lanes, gem_data, display, audio_ctrl, pitch_detector):
        super(Player, self).__init__()
        self.lanes = lanes
        self.num_lanes = len(lanes)
        self.display = display
        # self.audio = audio_ctrl

        self.slop_window = 0.1
        self.gem_data = gem_data
        self.gem_idx = [0]*self.num_lanes
        self.gem_status = [[False]*len(gem_data[lane]) for lane in gem_data]
        self.score = 10
        self.max_score = 10
        self.streak = 0
        self.longest_streak = self.streak

        self.gem_threshold = 0.25

        self.pitch = pitch_detector
        self.correct_pitch = 0
        self.cur_pitch = 0
        self.cor_lane = 0
        self.cur_gem = False # Tuple (lane, gem_idx)

        self.time = 0

    def get_score(self):
        return min(self.score/self.max_score, 1.0)

    def get_streak(self):
        return self.streak

    def get_longest_streak(self):
        return self.longest_streak

    def on_update(self, gametime):
        self.time = gametime
        # find the current gem (if there is one) and set self.correct_pitch
        for lane in range(self.num_lanes):
            gem_idx = self.gem_idx[lane]

            if lane in self.gem_data and gem_idx < len(self.gem_data[lane]):
                gem_time, duration, lyric = self.gem_data[lane][gem_idx]

                if gem_time < gametime < gem_time + duration:
                    self.correct_pitch = self.lanes[lane]
                    self.cur_gem = (lane, gem_idx)

                if gametime > gem_time + duration:
                    self.correct_pitch = 0
                    self.cur_gem = False
                    self.gem_idx[lane] += 1
                    self.max_score += 2

    def receive_audio(self, mono):
        if self.correct_pitch in self.lanes:
            self.cor_lane = self.lanes.index(self.correct_pitch)
        else:
            self.cor_lane = -1

        if self.cur_pitch != 0:
            conf = 0.5
        else:
            conf = 0.8
        self.cur_pitch = self.pitch.write(mono, conf)
        fs = 44100.

        if np.round(self.cur_pitch) == self.correct_pitch:
            # if you're correctly silent, smaller multiplier for score increase
            if np.round(self.cur_pitch) == 0:
                action = 'silent'
                self.score += 0.1*len(mono)/fs

            # if you're correctly singing a note, larger multiplier for score increase
            else:
                action = 'on'
                self.score += 5*len(mono)/fs
                # This is the bonus for hitting each note
                if not self.gem_status[self.cor_lane][self.gem_idx[self.cor_lane]]:
                    self.score += 2
                    self.gem_status[self.cor_lane][self.gem_idx[self.cor_lane]] = True
        
        # If you're singing when you're supposed to be silent 
        elif self.correct_pitch == 0:
            action = 'miss'
            self.score -= 0.1*len(mono)/fs

        # If you're silent when supposed to be singing, small penalty
        elif self.cur_pitch == 0:
            action = 'pass'
            self.score -= 0.1*len(mono)/fs

        # If you're singing the wrong note, you're penalized more based on how far off you are
        else:
            action = 'off'
            self.score -= 0.5*len(mono) * max(2,(np.round(self.cur_pitch) - self.correct_pitch))/fs

        # max score is just used for the percent calculation, don't worry about it
        self.score = max(0, self.score)
        if self.correct_pitch != 0: 
            self.max_score += 3*len(mono)/fs
        else:
            self.max_score += 0.1*len(mono)/fs

        self.display.animate_action(action, self.cur_gem)

run(MainWidget)
