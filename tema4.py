import json
import yaml

def valid_ip():
    while True:
        ip = input("Enter the ip address ('q' to exit): ")
        if ip == 'q':
            return ip

        bytes_ = ip.split(".")

        if len(bytes_) != 4:
            print("The ip address should be 4 bytes long! ")
            continue

        valid = True
        for byte in bytes_:
            if byte.isdigit():
                if not(0 <= int(byte) <= 255 and byte == str(int(byte))):
                    valid = False
                    break
            else:
                valid = False
                break

        if valid:
            print("The ip address is valid")
            return ip
        else:
            print("The ip address is invalid")



def get_device_info():

    result = {'switches': {}, 'routers': {}}
    assigned_ips = set()

    while True:
        device_type = input("Enter the device type ('switch' / 'router' / 'q' to exit): ")
        if device_type == 'q':
            break
        if device_type not in ('switch', 'router'):
            continue

        if device_type == 'switch':
            type_ = 'switches'
        else:
            type_ = 'routers'

        if device_type == 'switch':
            while True:
                sw_name = input("Enter the switch name ('q' to exit): ")
                if sw_name == 'q':
                    break
                if sw_name not in result[type_]:
                    result[type_][sw_name] = {}
                else:
                    print("The switch name already exists")
                    ow = input("Would you like to overwrite it? (y/n): ")
                    if ow == 'n':
                        continue

                while True:
                    sw_port = input("Enter the switch port ('q' to exit): ")
                    if sw_port == 'q':
                        break
                    if sw_port not in result[type_][sw_name]:
                        result[type_][sw_name][sw_port] = {}
                    else:
                        print("The switch port already exists")
                        ow = input("Would you like to overwrite it? (y/n): ")
                        if ow == 'n':
                            continue

                    speed = input("Enter the port speed ('q' to exit): ")
                    if speed == 'q':
                        result[type_][sw_name][sw_port]['speed'] = 'unassigned'
                        continue
                    result[type_][sw_name][sw_port]['speed'] = speed

                    ip = valid_ip()
                    if ip == 'q':
                        result[type_][sw_name][sw_port]['ip'] = 'unassigned'
                        continue
                    while ip in assigned_ips:
                        print("The ip address already exists, enter a new one. ")
                        ip = valid_ip()

                    assigned_ips.add(ip)
                    result[type_][sw_name][sw_port]['ip'] = ip


        if device_type == 'router':
            while True:
                r_name = input("Enter the router name ('q' to exit): ")
                if r_name == 'q':
                    break
                if r_name not in result[type_]:
                    result[type_][r_name] = {}
                else:
                    print("The router name already exists")
                    ow = input("Would you like to overwrite it? (y/n): ")
                    if ow == 'n':
                        continue

                while True:
                    r_port = input("Enter the router port ('q' to exit): ")
                    if r_port == 'q':
                        break
                    if r_port not in result[type_][r_name]:
                        result[type_][r_name][r_port] = {}
                    else:
                        print("The router port already exists")
                        ow = input("Would you like to overwrite it? (y/n): ")
                        if ow == 'n':
                            continue

                    speed = input("Enter the port speed ('q' to exit): ")
                    if speed == 'q':
                        result[type_][r_name][r_port]['speed'] = 'unassigned'
                        continue
                    result[type_][r_name][r_port]['speed'] = speed

                    ip = valid_ip()
                    if ip == 'q':
                        result[type_][r_name][r_port]['ip'] = 'unassigned'
                        continue
                    while ip in assigned_ips:
                        print("The ip address already exists, enter a new one. ")
                        ip = valid_ip()
                    assigned_ips.add(ip)
                    result[type_][r_name][r_port]['ip'] = ip






    print(result)
    jsn_result = json.dumps(result, indent=4)
    print(jsn_result)
    yml_result = yaml.dump(result)
    print(yml_result)

get_device_info()
