from PIL import Image
import numpy as np
from os import listdir
from os.path import isfile
import subprocess as sp
import asyncio
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
import configparser
from shutil import copyfile

from AppUI import AppUI
from Game import Game


# from GameObject import GameObject #not for main function


class AppController(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)

        self.loop = None
        self.uiObject = None
        self.subscriptionString = None
        self.subscription = None
        self.gameObject = None

        config_file = "options.ini"
        if not isfile(config_file):
            copyfile("default_options.ini", config_file)

        overwatch_config = self.open_config(config_file)

        self.debug_mode = overwatch_config["debug_mode"]
        self.game_version = overwatch_config["version"]
        self.bbox = (overwatch_config["start_pixel"], 0, overwatch_config["start_pixel"] + 1920, 1080)

        self.this_map = overwatch_config["map"]
        self.this_side = overwatch_config["side"]

    @staticmethod
    def open_config(config_file):
        config_parser = configparser.ConfigParser()
        config_parser.read(config_file)

        # TODO Fall-backs
        config = {
            "version": config_parser.get('Standard', 'Version'),
            "debug_mode": config_parser.get('Standard', 'Debug'),
            "map": config_parser.get('Debug', 'Map'),
            "side": config_parser.get('Debug', 'Side'),
            "start_pixel": int(config_parser.get('Standard', 'StartPixel'),)
        }
        return config

    async def onJoin(self, details):

        self.loop = asyncio.get_event_loop()

        # Initialize Game Object & obtain Subscription String
        self.uiObject = AppUI(self, self.loop)
        await self.uiObject.start_ui()

    async def subscribe_to_id(self, subscription_id):
        self.subscriptionString = 'com.voxter.teambuilder.' + subscription_id

        # Subscribe to the room so we receive events
        def on_event(msg1, msg2=None):
            # debug output
            if msg2 is None:
                print("Got event:")
                print("Argument 1: {" + str(msg1) + "}")
            else:
                print("Got event:")
                print("Argument 1: {" + str(msg1) + "}")
                print("Argument 2: {" + str(msg2) + "}")

            if msg1 == "Hello":
                self.gameObject.heroes.broadcast_heroes(self)
                self.gameObject.map.broadcast_options(self)
            elif msg1 == "heroes":
                self.gameObject.heroes.change_heroes(msg2)
            elif msg1 == "options":
                self.gameObject.map.currentMapSide = msg2[0]

        self.subscription = await self.subscribe(on_event, self.subscriptionString)
        self.gameObject = Game(self.game_version, self.bbox, self.debug_mode)
        self.publish(self.subscriptionString, "Hello")
        await asyncio.sleep(.5)
        while True:
            sleep_time = self.gameObject.main(self)
            await asyncio.sleep(sleep_time)

    def unsubscribe_from_current(self):
        self.subscription.unsubscribe()
        self.subscriptionString = None

    # -- supplementary functions -- #
    def create_hero_references(self):
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)

        reference_string = [
            'Reference\\HeroImageList.txt',
            'Reference\\HeroImageBlurList.txt',
        ]
        path = [
            "Reference\\Hero Image Sources",
            "Reference\\Hero Image Blur Sources"
        ]

        for x in range(0, len(reference_string)):
            reference_images_file = open(reference_string[x], 'w')
            reference_images = [image for image in listdir(path[x])]

            for file in reference_images:
                image_path = path[x] + "/" + file
                source_image = Image.open(image_path)
                source_image_array = np.array(source_image)
                threshold_image_array = this_game_object.heroes.threshold(source_image_array)
                source_image_list = threshold_image_array.tolist()
                condensed_source_image_list = self.condense_image(source_image_list)
                line_to_write = file[:-4] + '::' + str(condensed_source_image_list) + '\n'
                reference_images_file.write(line_to_write)
        print("Done")

    def create_images_for_hero_reference(self):
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)
        screen_img_array = this_game_object.get_screen()
        current_view = this_game_object.map.main(screen_img_array, "for_reference")
        hero_range = {"Hero Select": 7, "Tab": 13}
        for heroNumber in range(1, hero_range[current_view]):
            hero = this_game_object.heroes.heroesDictionary[heroNumber]
            this_game_object.heroes.identify_hero(screen_img_array, hero, current_view)
            hero.save_debug_data("for_reference")
        print("Done")

    def create_images_for_map_reference_hero_select(self):
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)
        screen_img_array = this_game_object.get_screen()
        this_game_object.map.currentImageArray = this_game_object.map.get_map(
            screen_img_array, "Hero Select", section='extended')  # , threshold_balance=True)
        this_game_object.map.save_debug_data("for_reference")
        print("Done")

    def create_images_for_map_reference_tab(self):
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)
        screen_img_array = this_game_object.get_screen()
        this_game_object.map.currentImageArray = this_game_object.map.get_map(screen_img_array, "Tab", section='normal')
        this_game_object.map.save_debug_data("for_reference")
        print("Done")

    def create_images_for_map_reference_objective(self):
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)
        screen_img_array = this_game_object.get_screen()
        this_game_object.map.current_map[0] = self.this_map
        this_game_object.map.currentMapSide = self.this_side
        this_game_object.map.reset_objective_progress()
        this_game_object.map.identify_objective_progress(screen_img_array, "for_reference")
        print("Done")

    def create_map_references(self):

        reference_string = [
            'Reference\\Letters.txt',
            'Reference\\MapImageListStandard.txt',
            'Reference\\MapImageListControl.txt',
            'Reference\\MapImageListArena.txt',
            'Reference\\MapImageListHybrid.txt',
            'Reference\\MapImageHighThreshold.txt',
            'Reference\\MapImageListTab.txt',
            'Reference\\MapImageListGameType.txt',
            'Reference\\ObjectiveListAssault.txt',
            'Reference\\ObjectiveListControl.txt',
            'Reference\\GameEnd.txt'
        ]
        path = [
            "Reference\\Letters",
            "Reference\\Map Name Image Sources\\Standard",
            "Reference\\Map Name Image Sources\\Control",
            "Reference\\Map Name Image Sources\\Arena",
            "Reference\\Map Name Image Sources\\Hybrid",
            "Reference\\Map Name Image Sources High Threshold",
            "Reference\\Map Name Tab Image Sources",
            "Reference\\Map Game Type Image Sources",
            "Reference\\Objective-Assault Sources",
            "Reference\\Objective-Control Sources",
            "Reference\\Game End Sources"]
        for x in range(0, len(reference_string)):
            reference_images_file = open(reference_string[x], 'w')
            reference_images = [image for image in listdir(path[x])]
            for file in reference_images:
                image_path = path[x] + "/" + file
                source_image = Image.open(image_path)
                source_image_array = np.array(source_image)
                # threshold_image_array = this_game_object.map.threshold(source_image_array)
                source_image_list = source_image_array.tolist()
                condensed_source_image_list = self.condense_image(source_image_list)
                line_to_write = file[:-4] + '::' + str(condensed_source_image_list) + '\n'
                reference_images_file.write(line_to_write)
        print("Done")

    def create_digit_images(self):
        sp.call('cls', shell=True)
        this_game_object = Game(self.game_version, self.bbox, self.debug_mode)
        screen_img_array = this_game_object.get_screen()
        this_game_object.gameTime.main(screen_img_array, "reference")
        print("Done")

    def create_digit_references(self):
        reference_string = ['Reference\\DigitImageList.txt', 'Reference\\ColonImageList.txt']
        path = ["Reference\\Digit Sources", "Reference\\Digit Colon Source"]
        for x in range(0, 2):
            reference_images_file = open(reference_string[x], 'w')
            reference_images = [image for image in listdir(path[x])]
            for file in reference_images:
                image_path = path[x] + "/" + file
                source_image = Image.open(image_path)
                source_image_array = np.array(source_image)
                # threshold_image_array = this_game_object.game_datetime.threshold(source_image_array)
                source_image_list = source_image_array.tolist()
                condensed_source_image_list = self.condense_image(source_image_list)
                line_to_write = file[:-4] + '::' + str(condensed_source_image_list) + '\n'
                reference_images_file.write(line_to_write)
        print("Done")

    @staticmethod
    def condense_image(image_list):
        new_image_list = []
        for row in image_list:
            new_image_list.append([])
            for pixel in row:
                new_image_list[-1].append(pixel[0])
        return new_image_list

    # @staticmethod
    # def unit_test_references():  # needs reworked
    #     # reference_image_list, temp1, temp2 = openReferences()  # need to add maps
    #
    #     path = "Reference\\Image Sources"
    #     reference_images = [image for image in listdir(path)]
    #     for file in reference_images:
    #         image_path = path + "/" + file
    #         source_image = Image.open(image_path)
    #         source_image_array = np.array(source_image)
    #         threshold_image_array = threshold(source_image_array)
    #         potential = whatCharacterIsThis(threshold_image_array, reference_image_list)
    #         character = max(potential.keys(), key=(lambda k: potential[k]))
    #         print(file)
    #         print(character)
    #         print(potential)
    #         print("")


def main_function():
    sp.call('cls', shell=True)
    runner = ApplicationRunner(url="wss://overwatch.johnelgin.me:8080/ws", realm="com.voxter.teambuilder")
    runner.run(AppController)


main_function()

# TODO List
'''
teams.js
    Javascript -> clean up for cleaner additions
    Allow two secondary healers instead of a primary
    Smart Flanker selection (flanker could also be a front line)
    Same for Main Tanks / Secondary
    Sound Alerts (?)
laravel
    Stats Tracking
    Login System
overwatch_app.py	
    Identify Objective Progress
        Keep track of progress
        Add Capture the Flag
    Keep track of Game Time
    Login System
    Detect Screen Resolution - Currently only 1080p
    Detect Screen Color Differences
    Streaming Integration
    GUI - Website instead of Tkinter?
'''