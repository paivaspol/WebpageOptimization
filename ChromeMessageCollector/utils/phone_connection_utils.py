import subprocess
import os

from time import sleep
from ConfigParser import ConfigParser

PCAP_DIRECTORY = '/sdcard/Research/output.pcap'
RESULT_DIRECTORY = '../result/'

DEVICE_ID = 'id'
IP = 'ip'
ADB_PORT = 'adb_port'
CHROME_DESKTOP_DEBUG_PORT = 'chrome_desktop_debugging_port'
DEVICE_TYPE = 'type'
CHROME_INSTANCE = 'chrome_instance'
WEB_SOCKET_DEBUGGER_URL = 'webSocketDebuggerUrl'
USE_CHROMIUM = 'use_chromium'

DEVICE_PHONE = 'phone'
DEVICE_MAC = 'mac'
DEVICE_UBUNTU = 'ubuntu'

ANDROID_CHROME_INSTANCE = 'com.android.chrome/com.google.android.apps.chrome.Main'
ANDROID_CHROMIUM_INSTANCE = 'org.chromium.chrome/com.google.android.apps.chrome.Main'
MAC_CHROME_INSTANCE = '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"'
UBUNTU_CHROME_INSTANCE = '"/opt/google/chrome/google-chrome"'

CHANGE_USER_AGENT = 'change_user_agent'
USER_AGENT = 'user_agent'
USER_AGENT_STR = 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 6 Build/MMB29S) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2645.0 Mobile Safari/537.36'

def start_chrome(device_configuration):
    '''
    Setup and run chrome on Android.
    '''
    if device_configuration[DEVICE_TYPE] == DEVICE_PHONE:
        # Setup port-forwarding for RDP
        cmd_base = 'adb -s {0} forward tcp:{1} localabstract:chrome_devtools_remote'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], device_configuration[ADB_PORT])
        p = subprocess.Popen(cmd, shell=True)

        # Run chrome
        cmd_base = 'adb -s {0} shell "am start -a android.intent.action.VIEW -n {1}"'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], device_configuration[CHROME_INSTANCE])
        p = subprocess.Popen(cmd, shell=True)

        sleep(3) # So we have enough time to forward the port.

        return p
    elif device_configuration[DEVICE_TYPE] == DEVICE_MAC or \
        device_configuration[DEVICE_TYPE] == DEVICE_UBUNTU:
        # print 'device config: ' + str(device_configuration)
        # Run Chrome.
        cmd = device_configuration[CHROME_INSTANCE] + ' --incognito --disable-extensions --remote-debugging-port={0} --ignore-certificate-errors --disable-logging > /dev/null 2>&1 &'.format(device_configuration[CHROME_DESKTOP_DEBUG_PORT])
        p = subprocess.call(cmd, shell=True)
        sleep(3)
        return p

def stop_chrome(device_configuration):
    '''
    Kill the chrome process that is running.
    '''
    if device_configuration[DEVICE_TYPE] == DEVICE_PHONE:
        chrome_instance = "com.android.chrome"
        if device_configuration[CHROME_INSTANCE] == ANDROID_CHROMIUM_INSTANCE:
            chrome_instance = "org.chromium.chrome"
        cmd_base = 'adb -s {0} shell am force-stop {1}'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], chrome_instance)
        # print cmd
        subprocess.call(cmd, shell=True)
    elif device_configuration[DEVICE_TYPE] == DEVICE_MAC:
        subprocess.call('pkill -9 Chrome', shell=True)
    elif device_configuration[DEVICE_TYPE] == DEVICE_UBUNTU:
        subprocess.call('pkill -9 chrome', shell=True)

def start_tcpdump(device_configuration):
    '''
    Starts tcpdump on the phone.
    '''
    tcpdump_started = False
    while not tcpdump_started:
        cmd_base = 'adb -s {0} shell \'su -c \'/tcpdump -i wlan0 -n -s 0 -w {1}\'\''
        cmd = cmd_base.format(device_configuration[DEVICE_ID], PCAP_DIRECTORY)
        retval = subprocess.Popen(cmd, shell=True)
        get_tcp_dump_process = 'adb -s {0} shell \'su -c \'ps | grep tcpdump\'\''.format(device_configuration[DEVICE_ID])
        result = subprocess.check_call(get_tcp_dump_process, shell=True)
        # print result
        tcpdump_started = True
    return retval

def stop_tcpdump(device_configuration, sleep_before_kill=True):
    '''
    Stops tcpdump on the phone.
    '''
    if sleep_before_kill:
        print 'Sleeping before killing tcpdump.'
        sleep(45) # Give sometime for tcpdump to be finished.
    cmd_base = 'adb -s {0} shell ps | grep tcpdump | awk \'{{ print $2 }}\' | xargs adb -s {0} shell "su -c kill -9"'
    cmd = cmd_base.format(device_configuration[DEVICE_ID])
    # print cmd
    return subprocess.Popen(cmd, shell=True)

def fetch_pcap(device_configuration, pcap_directory=PCAP_DIRECTORY, destination_directory=RESULT_DIRECTORY):
    '''
    Fetches the pcap file from the phone.
    '''
    fetch_file(device_configuration, pcap_directory, destination_directory, remove_file=True)

def fetch_cpu_measurement_file(device_configuration, measurement_dir, destination_directory):
    print 'Fetching CPU Measurement file...'
    fetch_file(device_configuration, measurement_dir, destination_directory, remove_file=True)

def fetch_file(device_configuration, file_location_on_phone, destination_directory, remove_file=False):
    print 'destination directory: ' + destination_directory
    cmd_base = 'adb -s {0} pull {1} {2}'
    cmd = cmd_base.format(device_configuration[DEVICE_ID], file_location_on_phone, destination_directory)
    os.system(cmd)
    if remove_file:
        cmd_base = 'adb -s {0} shell rm {1}'
        cmd = cmd_base.format(device_configuration[DEVICE_ID], file_location_on_phone)
        os.system(cmd)

def kill_cpu_measurement(device_configuration):
    command = 'adb -s {0} shell am force-stop edu.michigan.pageloadcpumeasurement'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True)

def start_cpu_measurement(device_configuration):
    command = 'adb -s {0} shell am start -n edu.michigan.pageloadcpumeasurement/.MainActivity'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True)

def bring_cpu_measurement_to_foreground(device_configuration):
    command = 'adb -s {0} shell am broadcast -a "android.intent.action.PROCESS_TEXT"'
    cmd = command.format(device_configuration[DEVICE_ID])
    subprocess.Popen(cmd, shell=True).wait()

def get_device_configuration(config_reader, device):
    '''
    Constructs a device configuration map.
    '''
    device_config = dict()
    device_config[IP] = config_reader.get(device, IP)
    device_type = config_reader.get(device, DEVICE_TYPE)
    device_config[DEVICE_TYPE] = device_type
    if device_type == DEVICE_PHONE:
        device_config[ADB_PORT] = int(config_reader.get(device, ADB_PORT))
        device_config[CHROME_INSTANCE] = ANDROID_CHROMIUM_INSTANCE if config_reader.get(device, USE_CHROMIUM) == 'True' else ANDROID_CHROME_INSTANCE
        device_config[DEVICE_ID] = config_reader.get(device, DEVICE_ID)
    elif device_type == DEVICE_MAC:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = MAC_CHROME_INSTANCE
        if config_reader.get(device, CHANGE_USER_AGENT) == 'True':
            device_config[USER_AGENT] = USER_AGENT_STR
    elif device_type == DEVICE_UBUNTU:
        device_config[CHROME_DESKTOP_DEBUG_PORT] = int(config_reader.get(device, CHROME_DESKTOP_DEBUG_PORT))
        device_config[CHROME_INSTANCE] = UBUNTU_CHROME_INSTANCE
        if config_reader.get(device, CHANGE_USER_AGENT) == 'True':
            device_config[USER_AGENT] = USER_AGENT_STR
    return device_config

def get_cpu_running_chrome(device_config):
    command = 'adb -s {0} shell \'ps -c | grep chrome\''.format(device_config[DEVICE_ID])
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = process.communicate()
    return output.split()[5]

def wake_phone_up(device_config):
    if device_config[DEVICE_TYPE] == DEVICE_PHONE:
        command = 'adb shell input keyevent KEYCODE_WAKEUP'
        subprocess.call(command, shell=True)
        print 'Waking up the phone'
