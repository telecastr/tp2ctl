import argparse
import re
from os import listdir
from os.path import realpath, join, isfile, isdir
from fcntl import ioctl
from struct import pack


HID_DEVICE_PATH = '/sys/bus/hid/devices'
DEVICE_PATH = '/dev'

POINTER_SPEEDS = [[0x13, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [0x13, 0x02, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]]

PREFERRED_SCROLLING_ENABLE = [0x13, 0x09,
                              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
PREFERRED_SCROLLING_DISABLE = [0x13, 0x09,
                               0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

# Generated using c++ macro HIDIOCSFEATURE(8)
HIDIOCSFEATURE_8 = 0xC0084806


def detect_tp2_keyboard():
    devices = listdir(HID_DEVICE_PATH)
    for device in devices:
        real_path = realpath(join(HID_DEVICE_PATH, device))
        # Get interface 1 of first device matching:
        # 17EF = VendorID Lenovo
        # 60EE = DeviceID TrackpointKeyboard2
        if re.match(r'.*1/....:17EF:60EE.*', real_path):
            return real_path
    return False


def get_hidraw_path(device):
    hidraw_path = join(device, 'hidraw')
    if not isdir(hidraw_path):
        return False
    hidraw_name = listdir(hidraw_path)[0]
    if not isdir(join(hidraw_path, hidraw_name)):
        return False
    return join(DEVICE_PATH, hidraw_name)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Control IBM Trackpoint 2 Keyboard features',
        epilog='Example usage: \'tp2ctl -s 8\'')
    parser.add_argument('-s', '--pointer-speed',
                        choices=range(0, 9), metavar='[0-8]', type=int,
                        help='set trackpoint sensitivity (\'Pointer Speed\')')
    parser.add_argument('-d', '--device',
                        metavar='DEVICE', type=file_path,
                        help='set hidraw device manually')
    arg_group = parser.add_mutually_exclusive_group()
    arg_group.add_argument('--no-preferred-scrolling',
                           dest='preferred_scrolling',
                           action='store_false',
                           help='enable \'Thinkpad Preferred Scrolling\'')
    arg_group.add_argument('--preferred-scrolling',
                           dest='preferred_scrolling',
                           action='store_true',
                           help='disable \'Thinkpad Preferred Scrolling\'')
    parser.set_defaults(preferred_scrolling=None)
    args = vars(parser.parse_args())
    if ((args["pointer_speed"] is None) and
            (args["preferred_scrolling"] is None)):
        parser.error('No arguments (e.g. pointer-speed) provided!')
    return args


def pack_payload(payload):
    return pack("BBBBBBBBB", *payload)


def send_payloads(hidraw_device, payloads):
    with open(hidraw_device, 'w') as fd:
        for payload in payloads:
            # Send payloads twice (as the Windows-Util does ...)
            ioctl(fd, HIDIOCSFEATURE_8, pack_payload(payload))
            ioctl(fd, HIDIOCSFEATURE_8, pack_payload(payload))


def main():
    args = parse_args()

    if args['device'] is not None:
        tp2_hidraw = args['device']
        print(f"Using hid-raw file handle '{tp2_hidraw}'")
    else:
        tp2_device_path = detect_tp2_keyboard()
        if not tp2_device_path:
            raise RuntimeError('Could not find Lenovo Trackpoint II Keyboard')
        print(f"Found Lenovo Trackpoint II Keyboard @ '{tp2_device_path}'")
        tp2_hidraw = get_hidraw_path(tp2_device_path)
        if not tp2_hidraw:
            raise RuntimeError(
                f"Could not open hid-raw device for {tp2_device_path}")
        print(f"Using hid-raw file '{tp2_hidraw}'")

    payloads = []

    if args['pointer_speed'] is not None:
        payloads.append(POINTER_SPEEDS[args['pointer_speed']])

    if args['preferred_scrolling'] is not None:
        if args['preferred_scrolling']:
            payloads.append(PREFERRED_SCROLLING_ENABLE)
        else:
            payloads.append(PREFERRED_SCROLLING_DISABLE)

    print("Sending Data ... ", end="")
    send_payloads(tp2_hidraw, payloads)
    print("Done!")


def file_path(path):
    if isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            f"readable_file:{path} is not a valid path")


if __name__ == '__main__':
    main()
