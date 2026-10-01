import socket
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

US_PORT = 8080


def dns_query(name, as_ip, as_port):
    message = f'TYPE=A\nNAME={name}\n'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(message.encode(), (as_ip, int(as_port)))
        data, _ = sock.recvfrom(4096)
        text = data.decode()
        print(f'[US] DNS response:\n{text}')
        for line in text.split('\n'):
            if line.startswith('VALUE='):
                value = line.split('=', 1)[1].strip()
                return value if value else None
        return None
    except socket.timeout:
        print('[US] DNS query timed out.')
        return None
    finally:
        sock.close()


@app.route("/fibonacci", methods=["GET"])
def fibonacci():
    hostname = request.args.get('hostname')
    fs_port = request.args.get('fs_port')
    number = request.args.get('number')
    as_ip = request.args.get('as_ip')
    as_port = request.args.get('as_port')

    missing = [
        k for k, v in {
            'hostname': hostname,
            'fs_port': fs_port,
            'number': number,
            'as_ip': as_ip,
            'as_port': as_port,
        }.items() if v is None
    ]
    if missing:
        return jsonify({'error': f'Missing parameters: {missing}'}), 400

    try:
        n = int(number)
    except ValueError:
        return jsonify({'error': 'number must be an integer'}), 400

    fs_ip = dns_query(hostname, as_ip, as_port)
    if not fs_ip:
        return jsonify({'error': f'Could not resolve hostname {hostname}'}), 500

    print(f'[US] Resolved {hostname} -> {fs_ip}')

    fs_url = f'http://{fs_ip}:{fs_port}/fibonacci?number={n}'
    print(f'[US] Forwarding to {fs_url}')
    try:
        resp = requests.get(fs_url, timeout=10)
    except requests.RequestException as e:
        return jsonify({'error': f'Failed to reach FS: {e}'}), 500

    if resp.status_code != 200:
        return jsonify({'error': 'FS returned an error', 'detail': resp.text}), 500

    try:
        data = resp.json()
    except ValueError:
        return jsonify({'error': 'FS returned invalid JSON', 'detail': resp.text}), 500

    return jsonify(data), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=US_PORT)