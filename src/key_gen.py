from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
import uuid
import msgpack

signing_key_src = SigningKey.generate()

verify_key = signing_key_src.verify_key.encode(encoder=HexEncoder)
signing_key = signing_key_src.encode(encoder=HexEncoder)
client_id = str(uuid.uuid4())

key_file = {
    "public_key": verify_key,
    "client_id": client_id,
    "notified": True,
    "last_online": 0
}

encoded_key = msgpack.packb(key_file)

with open('public_key', 'wb') as file:
    file.write(encoded_key)

key_file['private_key'] = signing_key

encoded_key = msgpack.packb(key_file)

with open('private_key', 'wb') as file:
    file.write(encoded_key)

print('Keys generated successfully')