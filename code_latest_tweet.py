"""
This will use Twitters Application Only Authorization to pull read data from twitter.  Data includes past tweets, follwers,
tweet favorites, retweets, and more.

Renamed file to "code.py" to run on pyportal
"""
# PyPortal LIbraries
import time
import gc
import json
import board
import busio
import neopixel
import displayio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

#Slightly Modfied version included in repo, 
# was added to pyportal source code so make sure you have latest version
from adafruit_pyportal import PyPortal   


#Internal Functions
from secrets import secrets
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

#GLOBAL VARIABLES
TWITTER_NAME = "Chewy_Turtle" #Twitter @<user__name) you want to track
TWEET_MODE = 'tweet_mode=extended' #Can be omitted from url to only get 140 characters (Old twitter limit)
PAST_TWEET_COUNT = '1' # How many tweets you're retrieving - String format so it's compatible with the URL
TWEET_INDEX = 0 #Index of tweets returned from call. 0 is always the latest tweet, range is 0 to (PAST_TWEET_COUNT - 1)
TWITTER_POST_URL = 'https://api.twitter.com/oauth2/token'
TWITTER_GET_URL = ('https://api.twitter.com/1.1/statuses/user_timeline.json?count='+ PAST_TWEET_COUNT + 
                '&screen_name=' + TWITTER_NAME + '&' + TWEET_MODE + '&' + '&exclude_replies=true&include_rts=false&trim_user=t')

POST_DATA = 'grant_type=client_credentials' #Needs to be string format, unlike how it works with the Py3 Requests Module


HEADERS_POST = {                        
    'Host'              : 'api.twitter.com',
    'User-Agent'        : 'PyPortal Twitter Application',
    'Authorization'     : 'Basic ' + secrets['encode_api_key_secret'],
    'Content-Type'      : 'application/x-www-form-urlencoded;charset=UTF-8',
    'Accept-Encoding'   : 'none',  
    }

HEADERS_GET = {                        
    'Host'              : 'api.twitter.com',
    'User-Agent'        : 'PyPortal Twitter Application',
    'Authorization'     : '',
    }

#LATEST_TWEET_USER_FOLLOWER_COUNT = [TWEET_INDEX, "user", "followers_count"]
# ^ ^^ Commented out because 'trim_user' vadriable in get request is set to true, which excludes the user information
# uncomment if you're not passing 'trim_user=t' or you're passing 'trim_user=f'

LATEST_TWEET_LOCATION = [TWEET_INDEX, "full_text"] #If Tweet Mode is changed, this will need to be "text" instead of "full_text"
TWEET_FAV_COUNT = [TWEET_INDEX, "favorite_count"]
RETWEET_COUNT = [TWEET_INDEX, "retweet_count"]

# the current working directory (where this file is)
CWD = ("/"+__file__).rsplit('/', 1)[0]

#Alert .wav files
NEW_FOLLOWER_SOUND = CWD+"/Coin.wav"
NEW_TWEET_SOUND = CWD+"/tweet.wav"

#initialize the Wifi Module - Needed outside of pyportal script so we can get the bearer token first before the Get request
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_gpio0 = DigitalInOut(board.ESP_GPIO0)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

esp32 = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Wifi is the object we're using to make the connection to the twitter API
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp32, secrets, status_light)

response = wifi.post(TWITTER_POST_URL, data=POST_DATA, headers=HEADERS_POST)

if response:
    print("Got Response from Post")
    response = response.json()
else:
    print("Failed to get Response from Twitter API - verify internet connection")

# The 'access_token' key in the json gives us the Bearer Token we need, if the key is present we can set that variable.
if 'access_token' in response.keys():
        #The Get function of the twitter API expects the token to start with 'Bearer ' so we're adding that here.
        HEADERS_GET['Authorization'] = 'Bearer ' +  response['access_token']
else:
    print('Twitter API Response did not include required access token.  Check your data in the secrets.py file.')

# Initialize the pyportal object and let us know what data to fetch and where to display it
pyportal = PyPortal(url = TWITTER_GET_URL,
                    headers = HEADERS_GET,
                    json_path =  [LATEST_TWEET_LOCATION, TWEET_FAV_COUNT, RETWEET_COUNT],
                    default_bg=CWD+"/latest_tweet_bkg.bmp",
                    text_font=CWD+"/fonts/PressStart2P-10.bdf",
                    #text_* variables need to be lists if we're passing > 1 json paths
                    text_position=[(30, 120),(30, 220),(280, 220)], 
                    text_color=[0xFFFFFF,0xF32E6D, 0x3ABD20],
                    text_wrap = [28,0,0],
                    text_maxlen = [240,10,10],
                    caption_text="Latest tweet from @"+ TWITTER_NAME,
                    caption_font=CWD+"/fonts/Collegiate-24.bdf",
                    caption_position=(25, 20),
                    caption_color=0xFFFFFF,
                    esp = esp32, #Pre defined the esp32 object before pyportal so we could do twitter handshake
                    passed_spi = spi,
                    )

pyportal.preload_font() #preload font to speed up processing

# track the last value so we can play a sound when it updates
pyportal_tweet = ''
followers_count = 0
num_likes = 0
num_rt = 0

while True:

    #Reset Flags before we check to see if the values changed
    updated_tweet = False
    retweet_update = False
    favorite_update = False

    #Call Twitter's get function with our get headers that now include the Bearer token required
    get_response = wifi.get(TWITTER_GET_URL, headers=HEADERS_GET)
    latest_tweet_data = get_response.json()

    #Check if latest tweet found is same as the current tweet displayed.
    if latest_tweet_data[TWEET_INDEX]['id'] != pyportal_tweet:
        updated_tweet = True
        pyportal_tweet = latest_tweet_data[TWEET_INDEX]['id']
        #set number of retweets and likes to 0 again for new tweet.
        num_likes = 0
        num_rt = 0
    #Check to see if number of favorites has increased.
    if latest_tweet_data[TWEET_INDEX]['favorite_count'] > num_likes:
        num_likes = latest_tweet_data[TWEET_INDEX]['favorite_count']
        favorite_update = True
    #Check if number of retweets is the same
    if latest_tweet_data[TWEET_INDEX]['retweet_count'] > num_rt:
        num_rt = latest_tweet_data[TWEET_INDEX]['retweet_count']
        retweet_update = True

    if updated_tweet or retweet_update or favorite_update:
        try:
            print('Fetching @' + TWITTER_NAME  + ' Feed ..')
            value = pyportal.fetch()
            pyportal_tweet = latest_tweet_data[TWEET_INDEX]['id']

            ### Uncomment to enable sounds ###
            # if updated_followers:
            #     pyportal.play_file(NEW_FOLLOWER_SOUND)
            # if updated_tweet:
            #     pyportal.play_file(NEW_TWEET_SOUND)

            print("Response is", value)
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)

    #need to close the connection to avoid memory overload
    gc.collect()
    time.sleep(60) #simple timer(seconds) to wait till looking for another tweet.