import socket

DNS_FILE = 'dns_records.txt'
UDP_PORT = 53533


def load_records():
    records = {}
    try:
        with open(DNS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = dict(p.split('=', 1) for p in line.split(" ") if '=' in p)
                name = parts.get('NAME')
                value = parts.get('VALUE')
                ttl = parts.get('TTL', '10')
                if name and value:
                    records[name] = (value, ttl)
    except FileNotFoundError:
        pass
    return records


def save_record(name, value, ttl):
    records = load_records()
    records[name] = (value, ttl)
    with open(DNS_FILE, 'w') as f:
        for n, (v, t) in records.items():
            f.write(f'TYPE=A NAME={n} VALUE={v} TTL={t}\n')


def parse_message(data):
    message = {}
    for line in data.split('\n'):
        line = line.strip()
        if '=' in line:
            key, val = line.split('=', 1)
            message[key.strip().upper()] = val.strip()
    return message


def build_message(fields):
    return '\n'.join(f'{k}={v}' for k, v in fields) + '\n'


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', UDP_PORT))
    print(f'[AS] Authoritative Server listening on UDP port {UDP_PORT}')

    while True:
        data, addr = sock.recvfrom(4096)
        text = data.decode('utf-8', errors='ignore')
        print(f'[AS] Received from {addr}:\n{text}')

        message = parse_message(text)
        message_type = message.get('TYPE', '').upper()
        name = message.get('NAME', '')

        if message_type != 'A' or not name:
            print('[AS] Invalid message (missing TYPE=A or NAME).')
            continue

        if 'VALUE' in message:
            value = message['VALUE']
            ttl = message.get('TTL', '10')
            save_record(name, value, ttl)
            print(f'[AS] Registered {name} -> {value} (TTL={ttl})')
            response = build_message([
                ('TYPE', 'A'),
                ('NAME', name),
                ('VALUE', value),
                ('TTL', ttl),
            ])
            sock.sendto(response.encode(), addr)
        else:
            records = load_records()
            if name in records:
                value, ttl = records[name]
                response = build_message([
                    ('TYPE', 'A'),
                    ('NAME', name),
                    ('VALUE', value),
                    ('TTL', ttl),
                ])
                print(f'[AS] Query for {name} -> returning {value}')
            else:
                response = build_message([
                    ('TYPE', 'A'),
                    ('NAME', name),
                    ('VALUE', ''),
                    ('TTL', '0'),
                ])
                print(f'[AS] Query for {name} -> NOT FOUND')
            sock.sendto(response.encode(), addr)


if __name__ == '__main__':
    main()