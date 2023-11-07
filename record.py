from pathlib import Path
import pyaudio
import wave
import random
import pygame

# use whisper
# hugging face

characters = "abcdefghijklmnopqrstuvwxyz1234567890"
cycles = 1

sampling_rate = 44100
chunk_size = 1024

p = pyaudio.PyAudio()
pygame.init()
screen = pygame.display.set_mode((200, 200))
font = pygame.font.SysFont("Menlo", 64)

def mainloop(prefix):
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sampling_rate,
        input=True,
        frames_per_buffer=chunk_size
    )

    for _ in range(cycles):
        remaining = list(characters)
        
        while len(remaining) > 0:
            c = random.choice(remaining)
            remaining.remove(c)

            text = font.render(c, True, (0, 0, 0))
            screen.fill((240, 240, 240))
            screen.blit(text, (100 - text.get_width() / 2, 100 - text.get_height() / 2))
            pygame.display.flip()

            stream.start_stream()

            frames = []
            remaining_loops = None
            while remaining_loops is None or remaining_loops > 0:
                frames.append(stream.read(chunk_size))

                event = pygame.event.poll()
                if event.type == pygame.NOEVENT:
                    pass
                elif event.type == pygame.QUIT:
                    stream.close()
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == ord(c):
                        remaining_loops = sampling_rate / chunk_size * 0.1 # 0.1 seconds

                if remaining_loops is not None:
                    remaining_loops -= 1

            stream.stop_stream()

            wf = wave.open(f"data/recording_{c}_{prefix}.wav", "wb")
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sampling_rate)
            wf.writeframes(b"".join(frames))
            wf.close()
                
prefix_path = Path("prefix.txt")
prefix = 0
if prefix_path.exists():
    with open(prefix_path, "r") as f:
        prefix = int(f.read())
with open(prefix_path, "w") as f:
    f.write(str(prefix + 1))

mainloop(prefix)

pygame.quit()
p.terminate()