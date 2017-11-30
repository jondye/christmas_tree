from blinkstick import blinkstick
from datetime import datetime
from jenkins import Jenkins
from random import randint
from time import sleep
import requests
import logging
import os


def pass_colours(max_rgb):
    colours = (
        (max_rgb/3, max_rgb/3, max_rgb/3),
        (max_rgb/2, max_rgb/2, 0),
        (max_rgb/2, 0, max_rgb/2),
        (0, max_rgb/2, max_rgb/2),
        (0, max_rgb, 0),
        (0, 0, max_rgb))
    while True:
        yield colours[randint(0, len(colours) - 1)]


def normal_colours():
    for r, g, b in pass_colours(255):
        yield r, g, b, 100


def morph(colours):
    r_start, g_start, b_start = 0, 0, 0
    for r_end, g_end, b_end, steps in colours:
        yield (r_start, g_start, b_start)

        for n in range(1, steps):
            d = 1.0 * n / steps
            r = (r_start * (1 - d)) + (r_end * d)
            g = (g_start * (1 - d)) + (g_end * d)
            b = (b_start * (1 - d)) + (b_end * d)

            yield (r, g, b)

        r_start, g_start, b_start = r_end, g_end, b_end


class BuildStatus(object):
    def __init__(self, server, name, poll_period=60):
        self.server = server
        self.name = name
        self.poll_period = poll_period
        self.last_poll = datetime(1970, 1, 1)
        self._colour = ''

    def build_colour(self):
        self.update_if_needed()
        return self._colour

    def led_colours(self):
        colours = pass_colours(255)
        while True:
            colour = self.build_colour()

            t = 100
            if colour.endswith('_anime'):
                t = 20
                yield 0, 0, 0, t

            if colour.startswith('blue'):
                r, g, b = next(colours)
                yield r, g, b, t
            elif colour.startswith('red'):
                yield 255, 0, 0, t
            else:
                yield 0, 0, 0, t

    def update_if_needed(self):
        time_since_last_poll = datetime.now() - self.last_poll
        if time_since_last_poll.seconds > self.poll_period:
            self.update()
            self.last_poll = datetime.now()

    def update(self):
        try:
            job = self.server.job(self.name)
            self._colour = job.info['color']
            logging.info("Build %s: %s", self.name, self._colour)
        except requests.exceptions.ConnectionError as e:
            logging.exception("Unable to connect for build status:\n" + str(e))
            self._colour = ''


class Tree(object):
    def __init__(self, colours, led_count=10):
        self.bstick = None
        self.last_poll = datetime(1970, 1, 1)
        self.led_count = led_count
        self.colours = [morph(c) for c in colours]

    def connect(self):
        self.bstick = blinkstick.BlinkStickPro(r_led_count=self.led_count)
        self.bstick.connect()

    def loop(self):
        try:
            while True:
                for index, colour in enumerate(self.colours):
                    r, g, b = next(colour)
                    self.bstick.set_color(channel=0, index=index, r=r, g=g, b=b)
                self.bstick.send_data_all()
                sleep(0.05)
        finally:
            if self.bstick:
                self.bstick.off()


def main():
    logging.basicConfig(level=logging.INFO)

    poll_period = os.environ.get('POLL_PERIOD', 60)
    server = os.environ.get('JENKINS_URI')
    build_names = [
        os.environ.get('JENKINS_JOB_%d' % (i+1))
        for i in range(10)
    ]

    j = Jenkins(server) if server else None
    lights = [
        BuildStatus(j, name).led_colours() if name else normal_colours()
        for name in build_names
    ]

    tree = Tree(lights)
    tree.connect()
    tree.loop()

if __name__ == '__main__':
    main()
