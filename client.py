import grpc
import encryption_pb2
import encryption_pb2_grpc
import rsa
import base64
import os

def generate_or_load_keys(private_key_path, public_key_path):
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        with open(private_key_path, "rb") as priv_file, open(public_key_path, "rb") as pub_file:
            private_key = rsa.PrivateKey.load_pkcs1(priv_file.read())
            public_key = rsa.PublicKey.load_pkcs1(pub_file.read())
        print("Loaded existing keys:")
    else:
        private_key, public_key = rsa.newkeys(2048)
        with open(private_key_path, "wb") as priv_file, open(public_key_path, "wb") as pub_file:
            priv_file.write(private_key.save_pkcs1())
            pub_file.write(public_key.save_pkcs1())
        print("Generated new keys:")
    print(f"Private Key: {private_key.save_pkcs1(format='PEM').decode('utf-8')}")
    print(f"Public Key: {public_key.save_pkcs1(format='PEM').decode('utf-8')}")
    return private_key, public_key

class EncryptionClient:
    def __init__(self, server_address):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = encryption_pb2_grpc.EncryptionServiceStub(self.channel)
        private_key_path = "keys/client_private.pem"
        public_key_path = "keys/client_public.pem"
        self.private_key, self.public_key = generate_or_load_keys(private_key_path, public_key_path)
        self.symmetric_key = None

    def exchange_key(self):
        public_key_pem = self.public_key.save_pkcs1(format='PEM').decode('utf-8')
        response = self.stub.ExchangeKey(
            encryption_pb2.KeyExchangeRequest(client_public_key=public_key_pem)
        )
        encrypted_key = base64.b64decode(response.encrypted_symmetric_key)
        self.symmetric_key = rsa.decrypt(encrypted_key, self.private_key)
        print("Symmetric key successfully exchanged!")

    def encrypt_message(self, message):
        if not self.symmetric_key:
            raise ValueError("Symmetric key not established. Call exchange_key first.")
        encrypted_message = base64.b64encode(message.encode()).decode('utf-8')
        return encrypted_message

    def decrypt_message(self, encrypted_message):
        if not self.symmetric_key:
            raise ValueError("Symmetric key not established. Call exchange_key first.")
        decrypted_message = base64.b64decode(encrypted_message.encode()).decode('utf-8')
        return decrypted_message

if __name__ == "__main__":
    client = EncryptionClient("localhost:50051")
    client.exchange_key()
    encrypted = client.encrypt_message("Hello, gRPC!")
    print("Encrypted message:", encrypted)
    decrypted = client.decrypt_message(encrypted)
    print("Decrypted message:", decrypted)
