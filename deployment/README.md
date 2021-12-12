# deployment

This document describes a process for a minimalistic deployment of Pisco
to a clean [Raspberry Pi Zero](https://www.raspberrypi.com/products/raspberry-pi-zero/)
with a [Pimoroni HyperPixel 4.0 Square](https://shop.pimoroni.com/products/hyperpixel-4-square?variant=30138251477075)
display.


## Prerequisites

In addition to your Pi hardware you are going to need a Linux or macOS machine running
[Raspberry Pi Imager](https://www.raspberrypi.com/software/) and
[Ansible](https://www.ansible.com).


## Setting up the operating system for the Pi Zero

[Use the Raspberry Pi Imager to create an SD card containing the operating system
*Raspberry Pi OS Lite (Legacy)*.](https://www.raspberrypi.com/documentation/computers/getting-started.html#using-raspberry-pi-imager)
Use the *Advanced options* menu to configure the operating system as follows:
1. Set the hostname to `pisco.local`.
2. Enable SSH.
3. Configure Wi-Fi.

After the SD card has been created, insert it into the Pi Zero and boot it.


## Setting up display drivers and Pisco on the Pi Zero

Once the Pi Zero has booted,
you can use the Ansible playbook `pisco.playbook.ansible.yml`
to install the display drivers and Pisco:
```shell
ansible-playbook pisco.playbook.ansible.yml
```

When the playbook has finished, you can manually
[set up your Bluetooth devices](https://howchoo.com/pi/bluetooth-raspberry-pi#setting-up-bluetooth-using-a-terminal-or-ssh-connection).
