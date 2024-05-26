import grpc
import pubsub_pb2
import pubsub_pb2_grpc
import time
from threading import Thread
import threading

GLOBAL_interuptions_lock = threading.Lock()


def listen_for_messages(stub, selected_channel):
    while True:  # Loop para intentar reconectar
        try:
            for message in stub.Subscribe(pubsub_pb2.Channel(name=selected_channel)):
                with GLOBAL_interuptions_lock:
                    print(f"Received message on channel '{selected_channel}': {message.content}")
        except grpc.RpcError as e:
            print(f"Stream closed with error: {e}, attempting to reconnect...")
            time.sleep(5)  # Espera antes de intentar reconectar
        else:
            print("Reconnection successful.")  # Se imprime cuando la reconexión es exitosa


def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = pubsub_pb2_grpc.PubSubStub(channel)

    # Obtener y mostrar la lista de canales disponibles
    channels = stub.ListChannels(pubsub_pb2.Empty())
    channel_names = [channel.name for channel in channels.channels]
    print("Canales disponibles:")
    for i, channel_name in enumerate(channel_names):
        print(f"{i + 1}. {channel_name}")

    # Solicitar al usuario que seleccione un canal
    selected_channel = None
    while selected_channel is None:
        try:
            choice = int(input("Seleccione un canal (número): "))
            if 1 <= choice <= len(channel_names):
                selected_channel = channel_names[choice - 1]
            else:
                print("Número fuera de rango. Inténtelo de nuevo.")
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número.")

    listener_thread = Thread(target=listen_for_messages, args=(stub, selected_channel))
    listener_thread.start()

    print("You can start sending messages. Type 'exit' to quit.")
    while True:
        with GLOBAL_interuptions_lock:
            message_content = input("Enter message to send: ")
        if message_content.lower() == 'exit':
            break
        stub.Publish(pubsub_pb2.Message(channel=selected_channel, content=message_content))
        time.sleep(0.1)

    listener_thread.join(timeout=2)
    channel.close()  # Asegúrate de cerrar el canal adecuadamente al finalizar.


if __name__ == '__main__':
    run()
