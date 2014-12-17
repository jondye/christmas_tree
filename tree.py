from blinkstick import blinkstick
from time import sleep
from random import randint
import datetime


RED = (255, 0, 0)
WHITE = (255, 255, 255)


def random_colours(max_rgb):
    while True:
        yield randint(0, max_rgb), randint(0, max_rgb), randint(0, max_rgb)


def christmas_colours(max_rgb):
    colours = ((max_rgb, 0, 0), (0, max_rgb, 0), (0, 0, max_rgb))
    while True:
        yield colours[randint(0, len(colours) - 1)]


def morph(colours, steps=100):
    r_start, g_start, b_start = 0, 0, 0
    for r_end, g_end, b_end in colours:
        yield (r_start, g_start, b_start)

        for n in range(1, steps):
            d = 1.0 * n / steps
            r = (r_start * (1 - d)) + (r_end * d)
            g = (g_start * (1 - d)) + (g_end * d)
            b = (b_start * (1 - d)) + (b_end * d)

            yield (r, g, b)

        r_start, g_start, b_start = r_end, g_end, b_end


def flash(colour, speed=20):
    def colours():
        while True:
            yield 0, 0, 0
            yield colour
    return morph(colours(), speed)


class Tree(object):
    def __init__(self, led_count=10):
        self.led_count = led_count
        self.colours = [morph(christmas_colours(20)) for _ in range(led_count)]
        self.red_flash = [flash(RED) for _ in range(led_count)]
        self.white_flash = [flash(WHITE) for _ in range(led_count)]

    def connect(self):
        self.bstick = blinkstick.BlinkStickPro(r_led_count=self.led_count)
        self.bstick.connect()

    def alert(self):
        return False

    def alarm(self):
        """Alarm at 11:45 for 30 seconds"""

        alarm_time = datetime.time(12, 45)
        now = datetime.datetime.now().time()
        return (alarm_time.hour == now.hour
                and alarm_time.minute == now.minute
                and now.second < 30)

    def select_colours(self):
        if self.alert():
            return self.red_flash

        if self.alarm():
            return self.white_flash

        return self.colours

    def loop(self):
        try:
            while True:
                colours = self.select_colours()
                for index in range(self.led_count):
                    r, g, b = next(colours[index])
                    self.bstick.set_color(channel=0, index=index, r=r, g=g, b=b)
                self.bstick.send_data_all()
                sleep(0.01)
        finally:
            self.bstick.off()


def main():
    tree = Tree()
    tree.connect()
    tree.loop()

if __name__ == '__main__':
    main()
