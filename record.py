from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from datetime import datetime
import threading
from typing import Any
import pyaudio
import wave
import json
import pygame
import time

# use whisper
# hugging face

screen_size = 500
padding = 50

audio = pyaudio.PyAudio()

class Recorder(threading.Thread):

    sampling_rate = 44100
    chunk_size = 1024

    def __init__(self) -> None:
        super().__init__()
        self._do_run = True
        self._recording = threading.Event()
        self._start_time: datetime | None = None
        self._data = b""
        self._stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sampling_rate,
            input=True,
            output=False,
            start=False,

            frames_per_buffer=self.chunk_size
        )
        self.start()

    def start_recording(self) -> None:
        self._data = b""
        self._stream.start_stream()
        self._start_time = datetime.now()
        self._recording.set()

    def stop_recording(self) -> tuple[bytes, datetime]:
        assert self._stream is not None
        assert self._start_time is not None
        self._recording.clear()
        return self._data, self._start_time
    
    def exit(self) -> None:
        self._do_run = False
        self.join()

    def run(self) -> None:
        while self._do_run:
            if self._stream is not None and self._recording.is_set():
                while self._do_run and self._recording.is_set():
                    self._data += self._stream.read(self.chunk_size)
                self._stream.stop_stream()
            self._recording.wait(timeout=0.1)
        if self._stream is not None:
            self._stream.close()
        print("exited")


paragraphs = []
with open("data.txt", "r") as f:
    data = f.read()
paragraphs = data.split("\n\n")

name = input("Enter your first name: ")

pygame.init()
screen = pygame.display.set_mode((screen_size, screen_size))
font = pygame.freetype.Font(None, 16) # type: ignore

sound_recorder = Recorder()

def line_breaks(text):
    max_width = screen_size - padding * 2
    words = text.split(" ")
    lines = []
    current_line = []
    current_width = 0

    for word in words:
        word_width = font.get_rect(" " + word).width
        if current_width + word_width > max_width:
            lines.append(" ".join(current_line))
            current_line = []
            current_width = 0
        current_line.append(word)
        current_width += word_width

    lines.append(" ".join(current_line))
    return lines

def render_line(line, color_at):
    offset = 2

    line_rect = font.get_rect(line)
    line_metrics = font.get_metrics(line)
    line_surface = pygame.Surface(line_rect.inflate(offset * 2, offset * 2).size)
    line_surface.fill((240, 240, 240))

    x = 0
    for i, (letter, metric) in enumerate(zip(line, line_metrics)):
        if i == color_at:
            pygame.draw.rect(
                line_surface,
                (180, 180, 180),
                pygame.Rect(x, 0, metric[4] + offset * 2, line_rect.height + offset * 2)
            )
        font.render_to(
            line_surface,
            (x + offset, line_rect.y + offset),
            letter
        )
        x += metric[4]

    return line_surface


def mainloop(prefix, name):

    s, r = font.render("Press any key to begin", (0, 0, 0))
    r.center = screen.get_rect().center
    screen.fill((240, 240, 240))
    screen.blit(s, r)
    pygame.display.flip()
    pygame.event.set_allowed([pygame.KEYDOWN, pygame.KEYUP, pygame.QUIT])

    ready = False
    while not ready:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYUP:
                ready = True

    time.sleep(1)
                
    for p in paragraphs:
        events = []
        pressed = {}

        screen.fill((240, 240, 240))

        lines = line_breaks(p)
        line_height = 20
        line_metrics = [font.get_metrics(l) for l in lines]

        for i, l in enumerate(lines):
            x = padding
            y = padding + i * line_height
            font.render_to(screen, (x, y), l)

        pygame.display.flip()

        sound_recorder.start_recording()

        for line_index, line in enumerate(lines):
            metrics = line_metrics[line_index]
            character_index = 0
            while character_index < len(line):
                character = line[character_index]
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.KEYDOWN:
                        events.append(["keydown", datetime.now().timestamp(), event.key, event.unicode])
                        pressed[event.key] = True
                    elif event.type == pygame.KEYUP:
                        events.append(["keyup", datetime.now().timestamp(), event.key, event.unicode])
                        if event.key in pressed:
                            if event.unicode == character:
                                r = pygame.Rect(
                                    padding + sum(metrics[i][4] for i in range(character_index)),
                                    padding + line_index * line_height,
                                    metrics[character_index][4],
                                    line_height
                                )
                                pygame.draw.rect(
                                    screen,
                                    (180, 180, 180),
                                    r
                                )
                                pygame.display.update(r)
                                character_index += 1

                            del pressed[event.key]
                        else:
                            print("WARNING: keyup without keydown, skipping event")

        screen.fill((240, 240, 240))
        pygame.display.flip()

        time.sleep(0.5)
        data, stream_start_time = sound_recorder.stop_recording()

        wf = wave.open(f"data/recording_{name}_{paragraphs.index(p)}_{prefix}.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sound_recorder.sampling_rate)
        wf.writeframes(data)
        wf.close()

        with open(f"data/events_{name}_{paragraphs.index(p)}_{prefix}.json", "w") as f:
            json.dump({
                "stream_start": stream_start_time.timestamp(),
                "events": events
            }, f)

prefix_path = Path("prefix.txt")
prefix = 0
if prefix_path.exists():
    with open(prefix_path, "r") as f:
        prefix = int(f.read())
with open(prefix_path, "w") as f:
    f.write(str(prefix + 1))

mainloop(prefix, name)

sound_recorder.exit()
print("done")
pygame.quit()
audio.terminate()