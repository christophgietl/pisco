# Pisco

Pisco is a keyboard only controller for Sonos speakers.

![Screenshot of Pisco while playing Kendrick Lamar's album 'DAMN.'](images/screenshot.png)

While Pisco's graphical interface displays the album art of the currently running track,
you can control playback with your keyboard.


## Setup

1. Make sure you are using Python 3.7 or newer.
2. Create a virtual environment if you do not want to clutter up your default environment.
3. Install dependencies:
    ```shell
    pip3 install --requirement requirements.txt
    ```


## Usage

When starting Pisco, you need to provide the name of the Sonos device (i.e. Sonos room) you want to control.

```shell
./pisco.py Leseecke # Replace 'Leseecke' by the name of your Sonos device.
```

You can use the option `--help` to find additional options:
```text
$ ./pisco.py --help                                                                                                                                                                                            master!
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
