from blinkstick import blinkstick
from time import sleep
from random import randint
from datetime import datetime, time, timedelta
import requests
import logging


RED = (255, 0, 0)
WHITE = (255, 255, 255)
STANDUP_TIME = time(11, 45)


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


def single_colour(colour):
    while True:
        yield colour


class BuildStatus(object):
    def __init__(self, branch):
        self.url = 'http://buildbot.eng.velocix.com/cgi-bin/results.py?page=recentbuilds&type=json&branch=%s&limit=1' % branch
        self.last_poll = datetime(1970, 1, 1)
        self.build_info = {}

    def failing(self):
        time_since_last_poll = datetime.now() - self.last_poll
        if time_since_last_poll.seconds > 300:
            logging.info("Polling build")
            try:
                self.build_info = requests.get(self.url).json()[0]
                logging.info("Build status: %s", self.build_info)
            except requests.exceptions.ConnectionError:
                logging.exception("Unable to connect to buildbot for build status")
            self.last_poll = datetime.now()
        return self.build_info.get('result', 0) != 0


class Tree(object):
    def __init__(self, led_count=10, brightness=20):
        self.bstick = None
        self.led_count = led_count
        self.colours = [morph(christmas_colours(brightness)) for _ in range(led_count)]
        self.red_flash = [flash(RED) for _ in range(led_count)]
        self.red = [single_colour((20, 0, 0)) for _ in range(led_count)]
        self.white_flash = [flash(WHITE) for _ in range(led_count)]
        self.alert_since = None
        self.build = BuildStatus('raptor')

    def connect(self):
        self.bstick = blinkstick.BlinkStickPro(r_led_count=self.led_count)
        self.bstick.connect()

    def alert(self):
        alert_condition = self.build.failing()

        if alert_condition and self.alert_since is None:
            self.alert_since = datetime.now()

        if not alert_condition and self.alert_since is not None:
            self.alert_since = None

        return alert_condition

    def alert_duration(self):
        if self.alert_since is None:
            return timedelta()

        return datetime.now() - self.alert_since

    def alarm(self):
        now = datetime.now().time()
        alarm_active = (STANDUP_TIME.hour == now.hour
                        and STANDUP_TIME.minute == now.minute)
        if alarm_active:
            logging.warning("Alarm: Daily Stand-Up")
        return alarm_active

    def select_colours(self):
        if self.alert():
            if self.alert_duration().seconds < 10:
                return self.red_flash
            return self.red

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
            if self.bstick:
                self.bstick.off()


def main():
    logging.basicConfig(level=logging.INFO)
    tree = Tree()
    tree.connect()
    tree.loop()

if __name__ == '__main__':
    main()
