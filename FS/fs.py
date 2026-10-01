import socket
from flask import Flask, request, jsonify

app = Flask(__name__)

FS_PORT = 9090


def fibonacci(n):
    if n < 0:
        raise ValueError('n must be >= 0')
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def register_with_as(hostname, ip, as_ip, as_port):
    message = (
        f'TYPE=A\n'
        f'NAME={hostname}\n'
        f'VALUE={ip}\n'
        f'TTL=10\n'
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(message.encode(), (as_ip, int(as_port)))
        data, _ = sock.recvfrom(4096)
        print(f'[FS] AS registration response:\n{data.decode()}')
        return True
    except socket.timeout:
        print('[FS] Registration timed out (no response from AS).')
        return False
    finally:
        sock.close()


@app.route("/register", methods=["PUT"])
def register():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'Invalid JSON body'}), 400

    required = ['hostname', 'ip', 'as_ip', 'as_port']
    missing = [k for k in required if k not in body]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    hostname = body['hostname']
    ip = body['ip']
    as_ip = body['as_ip']
    as_port = body['as_port']

    print(f'[FS] Registering {hostname} -> {ip} with AS at {as_ip}:{as_port}')
    success = register_with_as(hostname, ip, as_ip, as_port)

    if not success:
        return jsonify({'error': 'Failed to register with AS'}), 500

    return jsonify({'status': 'registered'}), 201


@app.route("/fibonacci", methods=["GET"])
def fib():
    num_str = request.args.get("number")
    if num_str is None:
        return jsonify({"error": "Missing 'number' parameter"}), 400

    try:
        n = int(num_str)
    except ValueError:
        return jsonify({'error': 'number must be an integer'}), 400

    if n < 0:
        return jsonify({'error': 'number must be >= 0'}), 400

    result = fibonacci(n)
    return jsonify({'number': n, 'fibonacci': result}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FS_PORT)