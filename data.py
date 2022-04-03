from rpi_epd2in7.epd import EPD
from PIL import Image, ImageFont, ImageDraw

from socket import gethostname
from shutil import disk_usage
from math import floor
from uptime import boottime
from datetime import datetime
from time import sleep
from requests import get
from netifaces import ifaddresses, AF_INET
from os import environ

SLEEP_TIME = 10

MOUNTED_DISK = "/media/disk"

EXTERNAL_IP_POOL = "https://ipecho.net/plain"
DATE_FORMAT = "%H:%M:%S %d/%m/%y"

DEBUG = False if environ.get("DEBUG") is None else True

def get_ip():
    return ifaddresses('eth0')[AF_INET][0]['addr']

def get_external_ip():
    response = get(EXTERNAL_IP_POOL)
    return response.text

def get_disk_space(path="/"):
    total, used, free = disk_usage(path)
    total_gb = floor(total / (1024 ** 3))
    used_gb = floor(used / (1024 ** 3))
    free_gb = floor(free / (1024 ** 3))

    return "%s/%sGB" % (free_gb, total_gb) 

def now():
    now = datetime.now()
    return now.strftime(DATE_FORMAT)


class Data:
    def __init__(self):
        self.hostname = None
        self.internal_ip = None
        self.external_ip = None
        self.diskspace = None
        self.booted = None
        self.refreshed = None

        self._get_data()

    def _get_data(self):
        self.hostname = gethostname()
        self.booted = boottime().strftime(DATE_FORMAT)

        self._refresh_data()

    def _refresh_data(self):
        self.refreshed = now()
        self.diskspace = get_disk_space(MOUNTED_DISK)
        self.internal_ip = get_ip()
        self.external_ip = get_external_ip()

    def is_same(self, old_data):
        return (old_data is not None 
        and self.hostname == old_data.hostname 
        and self.internal_ip == old_data.internal_ip 
        and self.external_ip == old_data.external_ip 
        and self.diskspace == old_data.diskspace)

BLACK = 0
WHITE = 255
ROW_HEIGHT = 20
ROW_PADDING = 2
FONT_SIZE = 15

FONT_FAMILY = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

class Drawer:
    def __init__(self, display):
        self.index = 0
        self.inverted_index = 1
        self.display = display
        self.inverted = False

        self.row_height = ROW_HEIGHT
        self.row_padding = ROW_PADDING

        self.font = ImageFont.truetype(FONT_FAMILY, FONT_SIZE)

    def _calc_row_height(self, rows):
        row_height = int(floor(self.display.width / len(rows)))

        padding = int(floor((row_height - FONT_SIZE) / 2))
        
        self.row_padding = padding
        self.row_height = row_height

    def draw_screen(self, rows):
        self._calc_row_height(rows)

        main_plane = Image.new('1', (self.display.width, self.display.height), WHITE)
        image = Image.new('1', (self.display.height, self.display.width), WHITE)
        draw = ImageDraw.Draw(image)

        for row in rows:
            self._draw_row(row, draw)
        
        image = image.rotate(90, expand=1) # rotate for screen

        main_plane.paste(image)
        self.display.smart_update(main_plane)

    def _draw_row(self, text, draw):
        index = self.index
        self.index = index + 1

        if len(text) == 0: # skip line if empty
            self.inverted = True
            return

        if not self.inverted:
            y = self.row_height * index
        else:
            index = self.inverted_index
            y = self.display.width - (self.row_height * index)
            self.inverted_index = index + 1

        colour_fill = BLACK # default to black font.

        if (index % 2) == 0:
            draw.rectangle((0, y, self.display.height, y + self.row_height), fill=BLACK)
            colour_fill = WHITE

        draw.text((5, y + self.row_padding), text, font=self.font, fill=colour_fill)


            
def structure_display(data_obj: Data):
    return [
        ["Hostname", data_obj.hostname],
        ["IP Address", data_obj.internal_ip],
        ["External IP", data_obj.external_ip],
        ["Disk", data_obj.diskspace],
        [],
        ["Booted", data_obj.booted],
        ["Refreshed", data_obj.refreshed],
    ]

def unify_and_construct(rows):
    padding_size = 0

    ret_rows = []

    group_longest = []

    longest = -1
    for row in rows:
        if len(row) == 0:
            group_longest.append(longest)
            longest = -1
            continue

        row_length = len(row[0])
        if row_length > longest:
            longest = row_length
    group_longest.append(longest)
    
    group_index = 0
    for row in rows:
        if len(row) == 0:
            ret_rows.append("") # blank row
            group_index = group_index + 1
            continue

        row_length = len(row[0])
        diff = group_longest[group_index] - row_length

        padding = ""
        for _ in range(diff + 1):
            padding = padding + " "
        
        new_row = "%s:%s%s" % (row[0], padding, row[1])
        ret_rows.append(new_row)

    return ret_rows

def main():   
    if DEBUG:
        print("initializing...")
        
    epd = EPD()
    epd.init()

    old_data = None
    try:
        while True:
            if DEBUG:
                print("Updating: %s" % now())

            current_data = Data()
            
            if current_data.is_same(old_data):
                sleep(SLEEP_TIME)
                continue
            else:
                if DEBUG:
                    print("New data refreshing! %s" % now())
                old_data = current_data

            build_structure = structure_display(current_data)

            rows = unify_and_construct(build_structure)

            Drawer(epd).draw_screen(rows)

            if DEBUG:
                print("\n----- Output -----")
                for row in rows:
                    print(row)
                print("----- Output -----\n")

            
    except KeyboardInterrupt:
        epd.sleep()
    
    if DEBUG:
        print("Exiting")


if __name__ == '__main__':
    main()
