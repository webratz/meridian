# Meridian
Scripts and tools to get informed if there are issues with Meridian trains

## Usage

### Get the notifications
Please note: The script parses the website which changed within the last year 3 times quite a lot. So it may be possible that the script simply stops working from one day to another.
There is absolutely no guarantee that this service works reliable!
#### on your phone or desktop computer
If you only want to use the output the scripts generates simply download PushBullet to your phone and subscribe to the Meridian channel via this link https://www.pushbullet.com/channel?tag=meridian

#### via twitter
Follow https://twitter.com/MeridianBahn


### Run it on your own
* Install the dependencies: ``` pip install -r requirements.txt```
* Change the config file ```meridian.toml```
* run the script with cron every few minutes

# FAQ
## Why I'm receiving some messages multiple times?
The script checks if the content of an announcment has changed. Even if there is only a minimal change the complete message will be sent again.

In some rare cases it might also happen that I had to clear the list of already sent notifications, so some are triggered again.

# Note
I'm **NOT** affiliated in any way with Meridian, I'm just using their services daily and the lack of a proper way to get relevant notifications was the reason to quickly hack some code.
