# Meridian
Scripts and tools to get informed if there are issues with Meridian trains

## Usage

### Get the notifications
If you only want to use the output the scripts generates simply download PushBullet to your phone and subscribe to the Meridian channel via this link https://www.pushbullet.com/channel?tag=meridian

Please note: The script parses the website which changed within the last year 3 times quite a lot. So it may be possible that the script simply stops working frome one day to another

### Run it on your own
* Install the dependencies: ``` pip install -r requirements.txt```
* Change the config file ```meridian.toml```
* run the script with cron every few minutes


# Note
I'm not affiliated in any way with Meridian, I'm just using their services daily and the lack of a proper way to get relevant notifications was the reason to quickly hack some code.
