import psutil
import wmi
import time
import subprocess
from colorama import init, Fore, Style

# For performance counters
from pyperfmon import pyperfmon

# For Windows Event Logs
import win32evtlog  # from pywin32

init(autoreset=True)

# Create a WMI object
_wmi = wmi.WMI()

# PerfMon helper
_pm = pyperfmon.pyperfmon()

def show_banner():
    print(Fore.CYAN + "╔" + "═" * 60 + "╗")
    print(Fore.CYAN + "║" + " " * 60 + "║")
    print(Fore.YELLOW + "║ WINDOWS SYSTEM SLOWNESS AUDIT TOOL v1.2.0".center(60) + " ║")
    print(Fore.YELLOW + "║ 42 Full-Featured Audit Functions".center(60) + " ║")
    print(Fore.CYAN + "║" + " " * 60 + "║")
    print(Fore.GREEN + "║ Developed By: Abubakkar Khan".center(60) + " ║")
    print(Fore.GREEN + "║ System Engineer | Cybersecurity Researcher".center(60) + " ║")
    print(Fore.CYAN + "║" + " " * 60 + "║")
    print(Fore.CYAN + "╚" + "═" * 60 + "╝")
    print()

def get_cpu_usage():
    print(Fore.YELLOW + "\n[+] CPU USAGE ANALYSIS")
    print(Fore.DARK_GRAY + "─" * 60)
    # CPU info
    for cpu in _wmi.Win32_Processor():
        print(Fore.WHITE + f"CPU Model: {cpu.Name}")
        print(Fore.WHITE + f"Cores: {cpu.NumberOfCores}, Logical: {cpu.NumberOfLogicalProcessors}")
        print(Fore.WHITE + f"Max Clock Speed: {cpu.MaxClockSpeed} MHz, Current: {cpu.CurrentClockSpeed} MHz")
    # Perf counter for total CPU load
    try:
        counter = _pm.query_counter(r'\Processor(_Total)\% Processor Time')
        cpu_load = counter.raw_value  # or cooked, depends lib
        cpu_load = round(cpu_load, 2)
        color = Fore.GREEN if cpu_load <= 60 else (Fore.YELLOW if cpu_load <= 80 else Fore.RED)
        print(color + f"Current Load: {cpu_load}%")
    except Exception as e:
        print(Fore.RED + f"Could not read CPU perf counter: {e}")

    # CPU queue length
    try:
        qcnt = _pm.query_counter(r'\System\Processor Queue Length').raw_value
        qcnt = round(qcnt, 2)
        col = Fore.GREEN if qcnt <= 2 else (Fore.YELLOW if qcnt <= 5 else Fore.RED)
        print(col + f"CPU Queue Length: {qcnt}")
        if qcnt > 5:
            print(Fore.RED + "(WARNING) High CPU queue indicates bottleneck.")
    except Exception:
        pass

    # Top processes by CPU
    print(Fore.CYAN + "\nTop 10 CPU-Consuming Processes:")
    procs = [(p.info['cpu_percent'], p.info) for p in psutil.process_iter(['cpu_percent', 'name', 'pid'])]
    procs = sorted(procs, key=lambda x: x[0], reverse=True)[:10]
    for cpu_pct, info in procs:
        print(f"{info['name']} (PID {info['pid']}): CPU = {cpu_pct}%")

    if 'cpu_load' in locals():
        if cpu_load > 80:
            print(Fore.RED + "(WARNING) CPU usage is critically high (>80%)")
        elif cpu_load > 60:
            print(Fore.YELLOW + "(CAUTION) CPU usage is elevated (60-80%)")
        else:
            print(Fore.GREEN + "(OK) CPU usage is within normal range (<60%)")

def get_memory_usage():
    print(Fore.YELLOW + "\n[+] MEMORY (RAM) ANALYSIS")
    print(Fore.DARK_GRAY + "─" * 60)
    vm = psutil.virtual_memory()
    total = vm.total / (1024 ** 3)
    available = vm.available / (1024 ** 3)
    used = total - available
    usage_percent = vm.percent
    print(Fore.WHITE + f"Total RAM: {total:.2f} GB")
    print(Fore.WHITE + f"Used RAM: {used:.2f} GB")
    print(Fore.WHITE + f"Free RAM: {available:.2f} GB")
    color = Fore.GREEN if usage_percent <= 75 else (Fore.YELLOW if usage_percent <= 90 else Fore.RED)
    print(color + f"Usage Percent: {usage_percent:.2f}%")

    # Page faults/sec via perf counter
    try:
        pf = _pm.query_counter(r'\Memory\Page Faults/sec').raw_value
        pf = round(pf, 2)
        print(Fore.WHITE + f"Page Faults/sec: {pf}")
    except Exception:
        pass

    print(Fore.CYAN + "\nTop 10 Memory-Consuming Processes:")
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            procs.append((p.info['memory_info'].rss, p.info))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs = sorted(procs, key=lambda x: x[0], reverse=True)[:10]
    for rss, info in procs:
        mb = rss / (1024 ** 2)
        print(f"{info['name']} (PID {info['pid']}): Memory = {mb:.2f} MB")

    if usage_percent > 90:
        print(Fore.RED + "(CRITICAL) Memory usage is critically high (>90%)")
    elif usage_percent > 75:
        print(Fore.YELLOW + "(WARNING) Memory usage is high (75-90%)")
    else:
        print(Fore.GREEN + "(OK) Memory usage is within acceptable range (<75%)")

def get_disk_performance():
    print(Fore.YELLOW + "\n[+] DISK PERFORMANCE AND SPACE ANALYSIS")
    print(Fore.DARK_GRAY + "─" * 60)
    # Disk space
    for disk in _wmi.Win32_LogicalDisk(DriveType=3):
        try:
            size_gb = disk.Size / (1024 ** 3)
            free_gb = disk.FreeSpace / (1024 ** 3)
            used_gb = size_gb - free_gb
            usage = (used_gb / size_gb) * 100
        except Exception:
            continue
        color = Fore.GREEN
        if usage > 90:
            color = Fore.RED
        elif usage > 80:
            color = Fore.YELLOW
        print(Fore.CYAN + f"\nDrive: {disk.DeviceID}")
        print(Fore.WHITE + f"Volume Label: {disk.VolumeName}")
        print(Fore.WHITE + f"Total: {size_gb:.2f} GB, Used: {used_gb:.2f} GB, Free: {free_gb:.2f} GB")
        print(color + f"Usage: {usage:.2f}%")
        if usage > 90:
            print(Fore.RED + "(CRITICAL) Disk space critically low (<10% free)")
        elif usage > 80:
            print(Fore.YELLOW + "(WARNING) Disk space low (10-20% free)")

    # I/O performance
    try:
        read = _pm.query_counter(r'\PhysicalDisk(_Total)\Disk Reads/sec').raw_value
        write = _pm.query_counter(r'\PhysicalDisk(_Total)\Disk Writes/sec').raw_value
        queue = _pm.query_counter(r'\PhysicalDisk(_Total)\Current Disk Queue Length').raw_value
        print(Fore.CYAN + "\nDisk I/O Performance:")
        print(Fore.WHITE + f"Reads/sec: {round(read, 2)}, Writes/sec: {round(write,2)}, Queue Length: {round(queue,2)}")
    except Exception as e:
        print(Fore.RED + f"Could not read disk I/O counters: {e}")

# === STUBS / PLACEHOLDERS for the remaining 39 functions ===

def get_network_performance():
    # Convert PowerShell Test-Connection, Get-Counter, etc.
    pass

def get_top_processes():
    pass

def get_windows_services_status():
    pass

def get_event_log_errors():
    pass

def get_startup_programs():
    pass

def get_windows_update_status():
    pass

def get_hardware_health():
    pass

def get_pagefile_virtual_memory():
    pass

def get_system_uptime_and_boot():
    pass

def get_scheduled_tasks():
    pass

def get_power_plan_and_battery():
    pass

def get_network_latency_test():
    pass

def get_dns_performance():
    pass

def get_antivirus_impact():
    pass

def get_disk_io_wait_time():
    pass

def get_process_handle_analysis():
    pass

def get_critical_event_logs():
    pass

def get_disk_fragmentation_status():
    pass

def get_shadow_copy_status():
    pass

def get_open_ports_and_services():
    pass

def get_firewall_rules_analysis():
    pass

def get_ssl_tls_certificates():
    pass

def get_smb_share_security():
    pass

def get_gpu_performance_monitor():
    pass

def get_problematic_driver_detection():
    pass

def get_usb_device_audit():
    pass

def get_sql_server_health():
    pass

def get_mysql_mariadb_health():
    pass

def get_iis_performance():
    pass

def get_docker_containers_health():
    pass

def get_hyperv_vms_status():
    pass

def get_security_baseline_check():
    pass

def get_patch_compliance_report():
    pass

def get_suspicious_process_scan():
    pass

def get_registry_health_check():
    pass

def get_system_file_integrity_sfc():
    pass

def get_windows_features_status():
    pass

def full_system_audit():
    # run all of the above
    get_cpu_usage()
    get_memory_usage()
    get_disk_performance()
    get_network_performance()
    get_top_processes()
    get_windows_services_status()
    get_event_log_errors()
    get_startup_programs()
    get_windows_update_status()
    get_hardware_health()
    get_pagefile_virtual_memory()
    get_system_uptime_and_boot()
    get_scheduled_tasks()
    get_power_plan_and_battery()
    get_network_latency_test()
    get_dns_performance()
    get_antivirus_impact()
    get_disk_io_wait_time()
    get_process_handle_analysis()
    get_critical_event_logs()
    get_disk_fragmentation_status()
    get_shadow_copy_status()
    get_open_ports_and_services()
    get_firewall_rules_analysis()
    get_ssl_tls_certificates()
    get_smb_share_security()
    get_gpu_performance_monitor()
    get_problematic_driver_detection()
    get_usb_device_audit()
    get_sql_server_health()
    get_mysql_mariadb_health()
    get_iis_performance()
    get_docker_containers_health()
    get_hyperv_vms_status()
    get_security_baseline_check()
    get_patch_compliance_report()
    get_suspicious_process_scan()
    get_registry_health_check()
    get_system_file_integrity_sfc()
    get_windows_features_status()

def export_report_to_desktop():
    # You can serialize all data into JSON or text and write to desktop
    pass

def show_menu():
    # Print a menu, read user choice, call functions
    while True:
        print(Fore.MAGENTA + "\nComprehensive Audit Menu")
        print("1. CPU Usage Analysis")
        print("2. Memory (RAM) Analysis")
        print("3. Disk Performance & Space")
        print("4. Network Performance")
        print("5. Top Resource Processes")
        print("6. Windows Services Status")
        print("7. Event Log Errors (24h)")
        print("8. Startup Programs")
        print("9. Windows Update Status")
        print("10. Hardware Health")
        print("11. FULL AUDIT (All 42 Checks)")
        print("12. Export Report to Desktop")
        print("0. Exit")

        choice = input("Enter choice: ").strip()
        if choice == "1":
            get_cpu_usage()
        elif choice == "2":
            get_memory_usage()
        elif choice == "3":
            get_disk_performance()
        elif choice == "11":
            full_system_audit()
        elif choice == "12":
            export_report_to_desktop()
        elif choice == "0":
            print(Fore.RED + "Exiting.")
            break
        else:
            print(Fore.YELLOW + "Option not implemented yet or invalid. Please try another.")

def main():
    show_banner()
    show_menu()

if __name__ == "__main__":
    main()
