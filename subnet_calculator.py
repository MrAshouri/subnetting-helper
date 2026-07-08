#!/usr/bin/env python3
"""Subnet Calculator for IP Planning"""

import csv
import ipaddress
import os


def get_network_range():
    """Get network range from user."""
    print("\n=== Subnet Calculator for IP Planning ===\n")
    print("Enter network in one of these formats:")
    print("  1. CIDR notation:  192.168.1.0/24")
    print("  2. IP range:       192.168.1.0 - 192.168.1.255")
    print()

    while True:
        raw = input("Network range: ").strip()
        if not raw:
            continue

        # CIDR notation
        if "/" in raw:
            try:
                return ipaddress.ip_network(raw, strict=False)
            except ValueError:
                print("Invalid CIDR. Try again.")

        # Range notation
        elif "-" in raw:
            parts = raw.split("-")
            try:
                start = ipaddress.ip_address(parts[0].strip())
                end = ipaddress.ip_address(parts[1].strip())
                # Build network from start/end by finding common prefix
                if int(start) > int(end):
                    print("Start IP must be <= End IP. Try again.")
                    continue
                # Convert range to CIDR (approximate)
                mask = _range_to_cidr(start, end)
                net = ipaddress.ip_network(f"{start}/{mask}", strict=False)
                return net
            except ValueError:
                print("Invalid IP addresses. Try again.")
        else:
            print("Unrecognized format. Use CIDR (x.x.x.x/N) or range (x.x.x.x - y.y.y.y).")


def _range_to_cidr(start, end):
    """Find the smallest prefix that covers the given range."""
    for prefix_len in range(32, -1, -1):
        net = ipaddress.ip_network(f"{start}/{prefix_len}", strict=False)
        if net.network_address <= start and net.broadcast_address >= end:
            return prefix_len
    return 0


def get_subnet_method():
    """Ask user how to subnet."""
    print("\nHow do you want to subnet?\n")
    print("  1. By number of subnets")
    print("  2. By hosts per subnet")
    print("  3. By custom prefix length")

    while True:
        choice = input("\nChoice (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        print("Enter 1, 2, or 3.")


def compute_subnets(network, method):
    """Compute subnets based on chosen method."""
    avail_bits = 32 - network.prefixlen

    if method == 1:
        while True:
            try:
                count = int(input("Number of subnets: "))
                if count <= 0:
                    print("Must be positive.")
                    continue
                if count > 2 ** avail_bits:
                    print(f"Too many. Max subnets with {network.prefixlen}-bit prefix: {2**avail_bits}")
                    continue
                # Find new prefix
                import math
                bits_needed = math.ceil(math.log2(count)) if count > 1 else 1
                new_prefix = network.prefixlen + bits_needed
                break
            except ValueError:
                print("Enter a valid number.")

    elif method == 2:
        while True:
            try:
                hosts = int(input("Minimum hosts per subnet: "))
                if hosts <= 0:
                    print("Must be positive.")
                    continue
                # Need enough host bits for hosts + network + broadcast
                needed = 0
                for h in range(hosts + 2, 2**33):
                    if h & (h - 1) == 0:
                        needed = h
                        break
                    # Actually just find next power of 2 >= hosts+2
                needed = 1
                while needed < hosts + 2:
                    needed <<= 1
                host_bits = needed.bit_length() - 1
                new_prefix = 32 - host_bits
                if new_prefix < network.prefixlen:
                    print("Not enough address space for this many hosts.")
                    continue
                break
            except ValueError:
                print("Enter a valid number.")

    elif method == 3:
        while True:
            try:
                new_prefix = int(input(f"New prefix length ({network.prefixlen + 1}-32): "))
                if new_prefix <= network.prefixlen:
                    print(f"Must be > {network.prefixlen}.")
                    continue
                if new_prefix > 32:
                    print("Max is 32.")
                    continue
                break
            except ValueError:
                print("Enter a valid number.")

    return new_prefix


def print_results(network, new_prefix):
    """Print subnet results."""
    subnets = list(network.subnets(new_prefix=new_prefix))
    hosts_per_subnet = 2 ** (32 - new_prefix) - 2

    print(f"\n{'=' * 65}")
    print(f"  Original Network:  {network}")
    print(f"  New Prefix:        /{new_prefix}")
    print(f"  Number of Subnets: {len(subnets)}")
    print(f"  Hosts per Subnet:  {hosts_per_subnet}")
    print(f"{'=' * 65}\n")

    # Table header
    print(f"{'#':<5} {'Subnet Address':<18} {'Range':<35} {'Broadcast':<18} {'Hosts'}")
    print(f"{'-'*5} {'-'*18} {'-'*35} {'-'*18} {'-'*7}")

    for i, sub in enumerate(subnets, 1):
        hosts = list(sub.hosts())
        if hosts:
            first_host = hosts[0]
            last_host = hosts[-1]
        else:
            first_host = last_host = sub.network_address
        print(f"{i:<5} {str(sub.network_address):<18} {str(first_host)} - {str(last_host):<16} {str(sub.broadcast_address):<18} {hosts_per_subnet}")

    # Summary for IP planning
    print(f"\n{'=' * 65}")
    print("  IP Planning Summary")
    print(f"{'=' * 65}")
    print(f"  Total addresses:  {2 ** (32 - network.prefixlen)}")
    print(f"  Usable hosts:     {hosts_per_subnet * len(subnets)}")
    print(f"  Overhead:         {2 * len(subnets)} (network + broadcast per subnet)")
    print()

    return subnets, hosts_per_subnet


def export_to_csv(subnets, hosts_per_subnet, network, new_prefix):
    """Export results to a CSV file in the script's directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_name = f"subnets_{str(network.network_address).replace('.', '_')}_{new_prefix}.csv"
    filename = input(f"Filename [{default_name}]: ").strip() or default_name

    if not filename.endswith(".csv"):
        filename += ".csv"

    filepath = os.path.join(script_dir, filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Subnet #", "Subnet Address", "First Host", "Last Host", "Broadcast", "Hosts"])

        for i, sub in enumerate(subnets, 1):
            hosts = list(sub.hosts())
            if hosts:
                first_host = str(hosts[0])
                last_host = str(hosts[-1])
            else:
                first_host = last_host = str(sub.network_address)
            writer.writerow([
                i,
                str(sub.network_address),
                first_host,
                last_host,
                str(sub.broadcast_address),
                hosts_per_subnet,
            ])

    print(f"\nExported to {filepath}")


def main():
    network = get_network_range()
    print(f"\nNetwork selected: {network} ({2**(32 - network.prefixlen)} addresses)")
    method = get_subnet_method()
    new_prefix = compute_subnets(network, method)
    subnets, hosts_per_subnet = print_results(network, new_prefix)

    export = input("Export to CSV? (y/n): ").strip().lower()
    if export == "y":
        export_to_csv(subnets, hosts_per_subnet, network, new_prefix)


if __name__ == "__main__":
    main()
