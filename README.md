# Pisco

Pisco is a keyboard only controller for Sonos speakers.
While Pisco's graphical interface displays the album art of the currently running track,
you can control playback with your keyboard.

<img src="images/screenshot.png" width="432" height="460" alt="Screenshot of Pisco while playing Kendrick Lamar's album DAMN.">

Pisco has been tested on Linux and on macOS.
It is particularly well-suited for usage with
small displays (e.g. [Pimoroni HyperPixel 4.0 Square](https://shop.pimoroni.com/products/hyperpixel-4-square?variant=30138251477075)) and
media remotes (e.g. [Satechi Bluetooth Multi-Media Remote](https://satechi.net/products/satechi-bluetooth-multi-media-remote?variant=27129644617)).


## Setup

1. Make sure you are using Python 3.7 or newer.
2. Create a virtual environment if you do not want to clutter up your default environment.
3. Clone this repository.
4. Install dependencies:
    ```shell
    pip3 install --requirement requirements.txt
    ```


## Usage

When starting Pisco,
you need to provide the name of the Sonos device (i.e. Sonos room) you want to control:

```shell
./pisco.py Leseecke # Replace 'Leseecke' by the name of your Sonos device.
```

You can use the option `--help` to find additional options:
```text
$ ./pisco.py --help
Usage: pisco.py [OPTIONS] SONOS_DEVICE_NAME

  Control your Sonos device with your keyboard

Options:
  -b, --backlight DIRECTORY    sysfs directory of the backlight that should be
                               deactivated when the device is not playing

  -w, --width INTEGER RANGE    width of the Pisco window  [default: 240]
  -h, --height INTEGER RANGE   height of the Pisco window  [default: 320]
  -r, --refresh INTEGER RANGE  time in milliseconds after which playback
                               information is updated  [default: 40]

  --help                       Show this message and exit.
```

As soon as Pisco is running, you can use the following keys to control playback:
- ⏯ (or return) to pause or resume playback
- ⏹ to stop playback
- ⏮ and ⏭ (or left and right arrow) to play previous or next track
- 0️⃣ to 9️⃣ to play the top 10 tracks (or radio stations) of your Sonos favorites
- ➕ and ➖ (or up and down arrow) to raise or lower volume
- 🔇 to mute or unmute
