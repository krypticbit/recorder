from pathlib import Path
from datetime import datetime
import pyaudio
import wave
import json
import pygame

# use whisper
# hugging face

sampling_rate = 44100
chunk_size = 1024

screen_size = 800
padding = 50

paragraphs = []
with open("data.txt", "r") as f:
    data = f.read()
paragraphs = data.split("\n\n")

audio = pyaudio.PyAudio()

name = input("Enter your first name: ")

pygame.init()
screen = pygame.display.set_mode((screen_size, screen_size))
font = pygame.freetype.Font(None, 16)
font.origin = True

stream = audio.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=sampling_rate,
    input=True,
    frames_per_buffer=chunk_size
)
stream.stop_stream()

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

    ready = False
    while not ready:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stream.close()
                pygame.quit()
                return
            elif event.type == pygame.KEYUP:
                ready = True
                

    for p in paragraphs:

        stream.start_stream()
        start_time = datetime.now()
        frames = []
        events = []
        pressed = {}

        lines = line_breaks(p)
        text = "".join(lines)
        remaining = list(text)
        while len(remaining) > 0:

            line_surfaces = []
            to_type = len(text) - len(remaining)

            for l in lines:
                line_surfaces.append(render_line(l, to_type))
                to_type -= len(l)
            
            line_height = max([l.get_rect().height for l in line_surfaces])
            y = padding
            screen.fill((240, 240, 240))
            for l in line_surfaces:
                screen.blit(l, (padding, y))
                y += line_height
            pygame.display.flip()

            loop = True
            while loop:
                frames.append(stream.read(stream.get_read_available()))
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        stream.close()
                        pygame.quit()
                        return
                    elif event.type == pygame.KEYDOWN:
                        delta_time = (datetime.now() - start_time)
                        events.append(["keydown", delta_time.total_seconds(), event.key, event.unicode])
                        pressed[event.key] = True
                        loop = False
                    elif event.type == pygame.KEYUP:
                        delta_time = (datetime.now() - start_time)
                        events.append(["keyup", delta_time.total_seconds(), event.key, event.unicode])
                        if event.key in pressed:
                            if event.unicode == remaining[0]:
                                loop = False
                                remaining = remaining[1:]
                            del pressed[event.key]
                        else:
                            print("WARNING: keyup without keydown, skipping event")

        screen.fill((240, 240, 240))
        pygame.display.flip()

        for _ in range(int(sampling_rate / chunk_size * 0.5)): # 0.5 second buffer at the end
            frames.append(stream.read(chunk_size))

        stream.stop_stream()

        wf = wave.open(f"data/recording_{name}_{paragraphs.index(p)}_{prefix}.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sampling_rate)
        wf.writeframes(b"".join(frames))
        wf.close()

        with open(f"data/events_{name}_{paragraphs.index(p)}_{prefix}.json", "w") as f:
            json.dump(events, f, indent=4)

prefix_path = Path("prefix.txt")
prefix = 0
if prefix_path.exists():
    with open(prefix_path, "r") as f:
        prefix = int(f.read())
with open(prefix_path, "w") as f:
    f.write(str(prefix + 1))

mainloop(prefix, name)

pygame.quit()
audio.terminate()