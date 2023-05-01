from dotenv import load_dotenv
from os import environ
from os.path import isfile
import socket
import msgpack
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

key_file = 'keys/private_key'

def form_message():
    key = None
    with open(key_file, 'rb') as file:
        key = file.read()
    key = msgpack.unpackb(key)

    signing_key = SigningKey(key["private_key"], encoder=HexEncoder)
    signed_msg = signing_key.sign(bytes(key["client_id"], 'utf-8'), encoder=HexEncoder)

    msg = {
        "client_id": key["client_id"],
        "signature": signed_msg
    }

    return msgpack.packb(msg)

def ping_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((server_address, server_port))
        msg = form_message()
        bs = client.send(msg)
        logging.info("{} bytes sent to server".format(bs))


if __name__ == '__main__':
    load_dotenv()

    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

    server_address = environ.get("SERVER_ADDR")
    server_port = environ.get("SERVER_PORT")
    sending_interval = environ.get("SENDING_INTERVAL")

    if not isfile(key_file):
        print("standart location is empty")
        key_file = input("please, enter new key path:")

    if sending_interval is None:
        sending_interval = 30
        logging.info("sending interval is not specified, defaulted to: {}".format(sending_interval))
    else:
        sending_interval = int(sending_interval)

    if server_address is None:
        logging.fatal("server address is invalid!")

    if server_port is None:
        logging.fatal("port is empty!")

    server_port = int(server_port)

    scheduler = BlockingScheduler()
    scheduler.add_job(ping_server, 'interval', seconds=sending_interval)

    try:
        logging.info("starting scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass