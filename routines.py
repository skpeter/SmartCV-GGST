import configparser
import time
import ggst
import re
import core.core as core
from core.matching import findBestMatch
from datetime import datetime
client_name = "smartcv-ggst"
config = configparser.ConfigParser()
config.read('config.ini')
previous_states = [None] # list of previous states to be used for state change detection

payload = {
    "state": None,
    "players": [
        {
            "name": None,
            "character": None,
            "rounds": 2,
        },
        {
            "name": None,
            "character": None,
            "rounds": 2,
        }
    ]
}

def detect_character_select_screen(payload:dict, img, scale_x:float, scale_y:float):
    pixel = img.getpixel((int(115 * scale_x), int(55 * scale_y))) #white tournament mode icon
    pixel2 = img.getpixel((int(1805 * scale_x), int(55 * scale_y))) #back button area
    
    # Define the target color and deviation
    target_color = (128, 30, 29)  #red player 1 side
    target_color2 = (18, 77, 107)  #blue player 2 side
    target_color3 = (187, 0, 3)  #red player 1 side
    target_color4 = (10, 108, 173)  #blue player 2 side

    deviation = 0.1
    
    conditions = [
        core.is_within_deviation(pixel, target_color, deviation),
        core.is_within_deviation(pixel2, target_color2, deviation),
        core.is_within_deviation(pixel, target_color3, deviation),
        core.is_within_deviation(pixel2, target_color4, deviation)
    ]

    if sum(conditions) == 2:
        payload['state'] = "character_select"
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Character select screen detected")
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            #clean up some more player information
            for player in payload['players']:
                player['rounds'] = 2
                player['character'] = None
                player['name'] = None
    return

def detect_characters(payload:dict, img, scale_x:float, scale_y:float):
    # signal to the main loop that character and tag detection is in progress
    if payload['players'][0]['character']: return
    # Initialize the reader
    region1 = (int(215 * scale_x), int(410 * scale_y), int(565 * scale_x), int(100 * scale_y))
    region2 = (int(215 * scale_x), int(600 * scale_y), int(565 * scale_x), int(100 * scale_y))
    character1 = core.read_text(img, region1)
    character2 = core.read_text(img, region2)
    if character1: character1 = ' '.join(character1)
    if character2: character2 = ' '.join(character2)

    if character1 is not None and character2 is not None:
        c1, score1 = findBestMatch(character1, ggst.characters)
        c2, score2 = findBestMatch(character2, ggst.characters)
        if score1 < 0.5 or score2 < 0.5: return
    else: return 
    payload['players'][0]['character'], payload['players'][1]['character'] = c1, c2
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 1 character:", c1)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 2 character:", c2)
    return

def detect_versus_screen(payload:dict, img, scale_x:float, scale_y:float):
    pixel1 = img.getpixel((int(1050 * scale_x), int(185 * scale_y))) #black letterbox
    pixel2 = img.getpixel((int(1050 * scale_x), int(195 * scale_y))) #blue sky
    
    # Define the target color and deviation
    target_color = (0, 0, 0)  #black letterbox
    target_color2 = (64, 132, 207)  #blue sky
    deviation = 0.1
    

    if core.is_within_deviation(pixel1, target_color, deviation) and core.is_within_deviation(pixel2, target_color2, deviation):
        payload['state'] = "loading"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Match is now loading...")
    return

def detect_player_tags(payload:dict, img, scale_x:float, scale_y:float):
    time.sleep(core.refresh_rate)
    if payload['players'][0]['name'] != None and payload['players'][1]['name'] != None: return

    tag1 = core.read_text(img, (int(575 * scale_x), int(35 * scale_y), int(770 * scale_x), int(115 * scale_y)))
    tag2 = core.read_text(img, (int(575 * scale_x), int(880 * scale_y), int(770 * scale_x), int(115 * scale_y)))
    if tag1: tag1 = ' '.join(tag1)
    if tag2: tag2 = ' '.join(tag2)

    if tag1 is not None and tag2 is not None:
        payload['players'][0]['name'], payload['players'][1]['name'] = tag1.strip(), tag2.strip()
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 1 tag:", payload['players'][0]['name'])
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 2 tag:", payload['players'][1]['name'])
    else:
        for player in payload['players']:
            player['name'] = False
    return

def detect_round_start(payload:dict, img, scale_x:float, scale_y:float):
    global ko_passes
    box = (int(960 * scale_x), int(475 * scale_y), int(10 * scale_x), int(180 * scale_y))

    if core.get_color_match_in_region(img, box, (200, 15, 15), 0.1) >= 0.9:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Game starting")
        for player in payload['players']:
            player['rounds'] = 2
        payload['state'] = "in_game"
        ko_passes = [0, 0]
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
                

def detect_rounds(payload:dict, img, scale_x:float, scale_y:float):
    """
    DEPRECATED
    """
    if payload['players'][0]['rounds'] < 2 and payload['players'][1]['rounds'] < 2: return
        
    pixel1 = img.getpixel((int(800 * scale_x), int(90 * scale_y))) #p1 heart
    pixel2 = img.getpixel((int(1120 * scale_x), int(90 * scale_y))) #p2 heart

    if config.getboolean('settings', 'debug_mode', fallback=False):
        print("Player 1 heart pixel:", pixel1, "Player 2 heart pixel:", pixel2)
    
    # Define the target color and deviation
    target_color = (213, 33, 48)  #red heart (still has round)
    target_color2 = (155, 155, 155)  #gray heart (lost round)
    deviation = 0.15

    if core.is_within_deviation(pixel1, target_color, deviation):
        if payload['players'][0]['rounds'] == 1: print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Correcting previous round loss report")
        payload['players'][0]['rounds'] = 2
    if core.is_within_deviation(pixel2, target_color, deviation):
        if payload['players'][1]['rounds'] == 1: print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Correcting previous round loss report")
        payload['players'][1]['rounds'] = 2
    if core.is_within_deviation(pixel1, target_color2, deviation):
        if payload['players'][0]['rounds'] != 1: print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 1 lost a round")
        payload['players'][0]['rounds'] = 1
    if core.is_within_deviation(pixel2, target_color2, deviation):
        if payload['players'][1]['rounds'] != 1: print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- Player 2 lost a round")
        payload['players'][1]['rounds'] = 1
    return

ko_passes = [0, 0]
def detect_ko(payload:dict, img, scale_x:float, scale_y:float):
    global ko_passes
    if len([p for p in ko_passes if p > 1]) > 0: return
    # we need to detect if the risc bar is there this means the HUD is being displayed and not being obstructed
    risc_pixel1 = img.getpixel((int(863 * scale_x), int(188 * scale_y)))
    risc_pixel2 = img.getpixel((int(1055 * scale_x), int(188 * scale_y)))
    empty_risc_color = (114, 118, 104)
    some_risc_color = (178, 10, 184)
    if config.getboolean('settings', 'debug_mode', fallback=False):
        print("Detected heart pixel - player 1:", risc_pixel1, "player 2:", risc_pixel2)
    conditions = [
        not core.is_within_deviation(risc_pixel1, empty_risc_color, 0.25),
        not core.is_within_deviation(risc_pixel2, empty_risc_color, 0.25),
        not core.is_within_deviation(risc_pixel1, some_risc_color, 0.25),
        not core.is_within_deviation(risc_pixel2, some_risc_color, 0.25)
    ]
    if (sum(conditions) > 2):
        if config.getboolean('settings', 'debug_mode', fallback=False):
            print("KO detection skipped, HUD not being displayed or obstructed")
        return

    pixel = img.getpixel((int(866 * scale_x), int(128 * scale_y)))
    pixel2 = img.getpixel((int(1052 * scale_x), int(128 * scale_y)))
    if config.getboolean('settings', 'debug_mode', fallback=False):
        print("KO detection pixels:", sum(pixel), sum(pixel2))
    dark_bar1 = True if sum(pixel) > 100 and sum(pixel) >= 200 else False
    dark_bar2 = True if sum(pixel2) > 100 and sum(pixel2) >= 200 else False
    if dark_bar1 ^ dark_bar2:
        if dark_bar1: ko_passes[0] += 1
        if dark_bar2: ko_passes[1] += 1
        if ko_passes[0] > 1 or ko_passes[1] > 1:
            core.print_with_time("SLASH", end=" ")
            winner = 0 if ko_passes[0] > 1 else 1
            payload['players'][not winner]['rounds'] -= 1
            print(f" - {payload['players'][winner]['character']}")
            if payload['players'][0]['rounds'] == 0 or payload['players'][1]['rounds'] == 0:
                core.print_with_time(f"{payload['players'][winner]['character']} wins!")
                payload['state'] = "game_end"
                if payload['state'] != previous_states[-1]:
                    previous_states.append(payload['state'])
            else:
                time.sleep(2)
                ko_passes = [0, 0]
        return
    ko_passes = [max(p - 1, 0) for p in ko_passes]
    return

def detect_results(payload:dict, img, scale_x:float, scale_y:float):
    if payload['players'][0]['rounds'] == 0 or payload['players'][1]['rounds'] == 0: return
    pixel = img.getpixel((int(1 * scale_x), int(105 * scale_y))) #the win/lose text for player 1
    pixel2 = img.getpixel((int(1 * scale_x), int(975 * scale_y))) #the win/lose text for player 1
    # Define the target color and deviation
    target_color = (140, 19, 5)  # red area on the top
    target_color2 = (36, 36, 36)  # gray area on the bottom
    deviation = 0.2
    if config.getboolean('settings', 'debug_mode', fallback=False):
        print("Detected result screen pixels - player 1:", pixel, "player 2:", pixel2)
        if ((core.is_within_deviation(pixel, target_color, deviation) and core.is_within_deviation(pixel2, target_color2, deviation))):
            pixel = img.getpixel((int(450 * scale_x), int(730 * scale_y))) # win box for player 1
            pixel2 = img.getpixel((int(1735 * scale_x), int(730 * scale_y))) # lose box for player 2
            target_color = (190, 0, 0)  # red
            target_color2 = (0, 80, 144) # blue
            if ((core.is_within_deviation(pixel, target_color, deviation) and core.is_within_deviation(pixel2, target_color2, deviation))):
                payload['players'][1]['rounds'] = 0
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"- {payload['players'][0]['character']} wins!")
            pixel = img.getpixel((int(555 * scale_x), int(730 * scale_y))) # lose box for player 1
            pixel2 = img.getpixel((int(1630 * scale_x), int(730 * scale_y))) # win box for player 2
            if ((core.is_within_deviation(pixel, target_color2, deviation) and core.is_within_deviation(pixel2, target_color, deviation))):
                payload['players'][0]['rounds'] = 0
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"- {payload['players'][1]['character']} wins!")
            else: 
                pixel = img.getpixel((int(1700 * scale_x), int(730 * scale_y))) # win box for online player
                pixel2 = img.getpixel((int(1815 * scale_x), int(730 * scale_y))) # lose box for online player
                if (core.is_within_deviation(pixel, target_color, deviation)):
                    payload['players'][1]['rounds'] = 0
                    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"- {payload['players'][0]['character']} wins!")
                elif (core.is_within_deviation(pixel2, target_color2, deviation)):
                    payload['players'][0]['rounds'] = 0
                    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"- {payload['players'][1]['character']} wins!")
            if payload['players'][0]['rounds'] == 0 or payload['players'][1]['rounds'] == 0:
                payload['state'] = "game_end"
                if payload['state'] != previous_states[-1]:
                    previous_states.append(payload['state'])
            time.sleep(core.refresh_rate)

states_to_functions = {
    None: [detect_character_select_screen, detect_versus_screen],
    "character_select": [detect_versus_screen],
    "loading": [detect_round_start, detect_characters, detect_player_tags],
    "in_game": [detect_character_select_screen, detect_ko, detect_results],
    "game_end": [detect_results, detect_character_select_screen, detect_round_start],
}