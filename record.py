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

paragraphs = []
with open("data.txt", "r") as f:
    data = f.read()
paragraphs = data.split("\n\n")

audio = pyaudio.PyAudio()

name = input("Enter your first name: ")

pygame.init()
screen = pygame.display.set_mode((500, 500))
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
    max_width = 450
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

def render_line(line, color_at = -1):
    line_rect = font.get_rect(line)
    line_metrics = font.get_metrics(line)
    line_surface = pygame.Surface(line_rect.size)
    line_surface.fill((240, 240, 240))

    x = 0
    for i, (letter, metric) in enumerate(zip(line, line_metrics)):
        font.render_to(line_surface, (x, line_rect.y), letter, (0, 0, 0) if i != color_at else (0, 160, 160))
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

        remaining = list(p)
        while len(remaining) > 0:

            line_surfaces = []
            to_type = len(p) - len(remaining)
            for l in line_breaks(p):
                if len(l) <= to_type:
                    line_surfaces.append(render_line(l))
                elif to_type >= 0:
                    line_surfaces.append(render_line(l, to_type))
                to_type -= len(l)
            
            line_height = max(s.get_height() for s in line_surfaces)
            x = 25
            y = 25

            screen.fill((240, 240, 240))
            for l in line_surfaces:
                screen.blit(l, (x, y))
                y += line_height
            pygame.display.flip()

            loop = True
            while loop:
                frames.append(stream.read(chunk_size))
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        stream.close()
                        pygame.quit()
                        return
                    elif event.type == pygame.KEYDOWN:
                        delta_time = (datetime.now() - start_time)
                        events.append(["keydown", delta_time.total_seconds(), event.key])
                        pressed[event.key] = True
                        loop = False
                    elif event.type == pygame.KEYUP:
                        delta_time = (datetime.now() - start_time)
                        events.append(["keyup", delta_time.total_seconds(), event.key])
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