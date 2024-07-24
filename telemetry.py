import psutil
import json
import requests
import time
import sys
import subprocess
import logging

from datetime import datetime

from zap import active_scans_count, is_zap_online, start_scan, get_all_scan_results

from dataclasses import dataclass


@dataclass
class Site:
    url: str
    context: str = "Default Context"


# Author : HunterBounter

def send_scan_results(scan_results):
    try:
        response = requests.post('https://panel.hunterbounter.com/scan_results/save', data=scan_results)
        if response.status_code != 200:
            print(f"Failed to send scan results: {response.text}")
    except Exception as e:
        print(f"Failed to send scan results: {e}")


def get_host_name():
    try:
        host_name = subprocess.run(['hostname'], capture_output=True, text=True)
        return host_name.stdout.strip()
    except Exception as e:
        return f"Hata: {e}"


def find_command_path(command):
    try:
        result = subprocess.run(['which', command], capture_output=True, text=True)
        # Komutun yolunu döndür
        return result.stdout.strip()
    except Exception as e:
        return f"Hata: {e}"


def get_active_interfaces():
    if_addrs = psutil.net_if_addrs()
    active_interfaces = {interface: addrs[0].address for interface, addrs in if_addrs.items() if addrs}
    return active_interfaces


def get_cpu_serial():
    # CPU seri numarasını elde etme
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return line.split(':')[1].strip()
    except Exception as e:
        return str(e)


def convert_bytes_to_gb(bytes_value):
    return bytes_value / (1024 * 1024 * 1024)


def classify_status(value, normal_threshold, medium_threshold):
    if value < normal_threshold:
        return "NORMAL"
    elif value < medium_threshold:
        return "MEDIUM"
    else:
        return "CRITICAL"


def get_uptime():
    uptime_seconds = int(time.time() - psutil.boot_time())
    uptime_days = uptime_seconds // (24 * 60 * 60)
    uptime_seconds %= (24 * 60 * 60)
    uptime_hours = uptime_seconds // (60 * 60)
    uptime_seconds %= (60 * 60)
    uptime_minutes = uptime_seconds // 60
    return f"{uptime_days} days, {uptime_hours} hours, {uptime_minutes} minutes"


def get_disk_status(used_percent):
    if used_percent < 70:
        return "NORMAL"
    elif used_percent < 90:
        return "MEDIUM"
    else:
        return "CRITICAL"


def get_server_stats():
    try:
        hostname = get_host_name()

        ram_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent()
        active_interfaces = get_active_interfaces()
        # Disk kullanımı istatistikleri
        disk_usage = psutil.disk_usage('/')

        disk_usage_percent = disk_usage.percent

        total_scan_count = 0
        total_scan_response = active_scans_count()
        logging.info("Total scan response: " + str(total_scan_response))
        if total_scan_response['success']:
            total_scan_count = total_scan_response['message']

        zap_response = is_zap_online()

        zap_status = "offline"
        if zap_response['success']:
            zap_status = "online"

        # Sistem uptime
        uptime = get_uptime()

        stats = {
            "hostname": hostname,
            "telemetry_type": "zap",
            "active_scan_count": total_scan_count,
            "zap_status": zap_status,
            "active_interfaces": active_interfaces,
            "uptime": uptime,
            "ram_usage": ram_usage,
            "cpu_usage": cpu_usage,
            "active_connections": len(psutil.net_connections()),
            "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if zap_status == "online":
            logging.info("Getting targets")
            target_response = get_targets(total_scan_count, 1)

            if target_response['success']:
                logging.info("Targets received")
                logging.info("Response -> " + str(target_response))

                targets = target_response['data']['targets']

                if targets is not None:
                    for target in targets:
                        logging.info(f"Sending scan result for {target}")
                        if not target.startswith("http://") and not target.startswith("https://"):
                            target = "http://" + target

                        site = Site(url=target)

                        start_scan_response = start_scan(site)
                        logging.info(f"Start scan response: {start_scan_response}")

        return stats
    except Exception as e:
        print(f"Failed to get server stats: {e}")
        return {"success": False, "message": str(e)}


def get_targets(total_running_scan_count, docker_type):
    url = "https://panel.hunterbounter.com/target"
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "total_running_scan_count": total_running_scan_count,
        "docker_type": docker_type
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        logging.info(f"Response: {response.json()}")
        if response.status_code == 200:
            print(f"Success: {response.json()}")
            return response.json()
        else:
            print(f"Failed to get targets: {response.text}")
            return {"success": False, "message": response.text}
    except Exception as e:
        print(f"Failed to get targets: {e}")
        return {"success": False, "message": str(e)}


# Example usage


def send_telemetry(json_stats):
    try:
        response = requests.post('https://panel.hunterbounter.com/telemetry/save', data=json_stats)
        if response.status_code != 200:
            print(f"Failed to send telemetry data: {response.text}")
    except Exception as e:
        print(f"Failed to send telemetry data: {e}")


def send_scan_telemetry():
    try:
        scan_results = get_all_scan_results()

        #scan results is raise ?
        if scan_results is None:
            logging.info("Scan results is None")
            return
            # to json

        # add machineId
        hostname = get_host_name()

        # Add machine ID to each scan result
        for result in scan_results:
            result['machine_id'] = hostname
        scan_results = json.dumps(scan_results, indent=4)

        response = requests.post('https://panel.hunterbounter.com/scan_results/save', data=scan_results, headers={"Content-Type": "application/json"})
        if response.status_code != 200:
            print(f"Failed to send scan results: {response.text}")
    except Exception as e:
        print(f"Failed to send scan results: {e}")


server_stats = get_server_stats()
json_stats = json.dumps(server_stats, indent=4)
send_telemetry(json_stats)
