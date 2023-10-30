from dotenv import load_dotenv
from os import environ
from os.path import isfile
import socket
import msgpack
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from paho.mqtt import client as mqtt_client
import random
import topics
import time

key_file = 'keys/private_key'
KEEP_ALIVE_REQUEST = 0
IP_ADDRESS_REQUEST = 1

def form_message():
    key = None
    with open(key_file, 'rb') as file:
        key = file.read()
    key = msgpack.unpackb(key)

    signing_key = SigningKey(key["private_key"], encoder=HexEncoder)
    signed_msg = signing_key.sign(bytes(key["client_id"], 'utf-8'), encoder=HexEncoder)

    msg = {
        "client_id": key["client_id"],
        "signature": signed_msg,
        "request_type": KEEP_ALIVE_REQUEST
    }

    return msgpack.packb(msg)

def ping_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((server_address, server_port))
        msg = form_message()
        bs = client.send(msg)
        logging.info("{} bytes sent to server".format(bs))

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT")
    else:
        logging.fatal("Failed to connect to MQTT, return code: %d\n", rc)

def on_mqtt_message(client: mqtt_client.Client, userdata, msg):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sck:
        sck.connect((server_address, server_port))
        msg = {
            'request_type': IP_ADDRESS_REQUEST
        }

        bs = sck.send(msgpack.packb(msg))
        logging.info("%d bytes sent to server", bs)
        result = sck.recv(1024)
        result = msgpack.unpackb(result)
        result_addr = result['ip_address']
        client.publish(topic=topics.SEND_MESSAGE, payload=f"homeserver ip address: {result_addr}")

def start_mqtt(broker: str, port: int = 1883, broker_username : str | None = None, broker_password: str | None = None):
    client_id = "link-client-{}".format(random.randint(0, 1000))
    client = mqtt_client.Client(client_id=client_id)
    client.on_connect = on_mqtt_connect
    if broker_username is not None:
        client.username_pw_set(broker_username, broker_password)
    client.connect(broker, port=port)
    client.loop_start()

    client.subscribe(topic=topics.GET_IP_ADDRESS)
    client.on_message = on_mqtt_message

if __name__ == '__main__':
    load_dotenv()

    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

    server_address = environ.get("SERVER_ADDR")
    server_port = environ.get("SERVER_PORT")
    sending_interval = environ.get("SENDING_INTERVAL")

    broker_host = environ.get("MQTT_HOST")
    if broker_host is None:
        logging.fatal("could not load mqtt host")
    else:
        logging.info("MQTT host: %s", broker_host)
    broker_port = environ.get("MQTT_PORT")
    if broker_port is None:
        broker_port = 1883
    else:
        broker_port = int(broker_port)
    logging.info("MQTT port: %d", broker_port)

    broker_username = environ.get("MQTT_USERNAME")
    broker_password = environ.get("MQTT_PASSWORD")

    if not isfile(key_file):
        logging.error("standart location is empty")
        time.sleep(600)
        logging.fatal("key file not found")

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

    start_mqtt(broker_host, broker_port=broker_port, broker_username=broker_username, broker_password=broker_password)

    try:
        logging.info("starting scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass