# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

#Rename file to 'secrets.py' when you ifnromation is populated.
secrets = {
    'ssid' : '', 
    'password' : '',
    'timezone' : "America/Denver", # http://worldtimeapi.org/timezones
    'github_token' : '',
    #encode_api_key_secret: a base 64 encrypted string of a twitter app api in <consumer-key>-<consumer-secret>
    # see step one here. https://developer.twitter.com/en/docs/basics/authentication/overview/application-only
    # can use an online base64 encode tool to get the encoded string you need.
    'encode_api_key_secret' : '',
    }
