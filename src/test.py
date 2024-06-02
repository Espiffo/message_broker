import threading
import grpc
import random
import pubsub_pb2
import pubsub_pb2_grpc
import time

def publisher_thread(channel_name, server_address="localhost:50051"):
    # Establecer la conexión con el servidor gRPC
    channel = grpc.insecure_channel(server_address)
    stub = pubsub_pb2_grpc.PubSubStub(channel)
    try:
        while True:
            # Generar contenido aleatorio para el mensaje
            content = f"Random message {random.randint(100, 999)} from {threading.current_thread().name}"
            response = stub.Publish(pubsub_pb2.Message(channel=channel_name, content=content))
            if response.success:
                print(f"Published: {content} on channel {channel_name}")
            else:
                print(f"Failed to publish: {content} on channel {channel_name}")
            time.sleep(random.uniform(1, 3))  # Esperar un tiempo aleatorio antes de enviar otro mensaje
    except grpc.RpcError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    threads = []
    channel_name = "test"  # Asumiendo que 'test' es uno de los canales disponibles

    # Crear 20 hilos de publicador
    for i in range(1):
        thread = threading.Thread(target=publisher_thread, args=(channel_name,))
        threads.append(thread)
        thread.start()

    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()
