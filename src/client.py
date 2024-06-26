import queue

import grpc
import pubsub_pb2
import pubsub_pb2_grpc
import time
from threading import Thread, Event
import threading

GLOBAL_interuptions_lock = threading.Lock()
my_messages = queue.Queue()


class ConnectionState:
    def __init__(self):
        self.condition = threading.Condition()
        self.is_connected = False

    def wait_for_connection(self):
        with self.condition:
            while not self.is_connected:
                self.condition.wait()

    def set_connected(self, connected):
        with self.condition:
            self.is_connected = connected
            if connected:
                self.condition.notify_all()  # Notificar a todos los hilos en espera cuando la conexión esté establecida


def check_connection(health_stub, stop_event, connection_state):
    backoff = 2
    max_backoff = 8
    while not stop_event.is_set():
        try:
            health_stub.Ping(pubsub_pb2.Empty())
            connection_state.set_connected(True)
            backoff = 1
        except grpc.RpcError:
            connection_state.set_connected(False)
            print(f"Connection lost, attempting to reconnect in {backoff} seconds...")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
    return


def get_channel_selection(stub):
    channels = stub.ListChannels(pubsub_pb2.Empty())
    channel_names = [channel.name for channel in channels.channels]
    print("Canales disponibles:")
    for i, channel_name in enumerate(channel_names):
        print(f"{i + 1}. {channel_name}")

    selected_channels = []
    while True:
        choice = input("Seleccione un canal por número (o 'done' para terminar): ")
        if choice.lower() == 'done':
            break
        try:
            choice = int(choice)
            if 1 <= choice <= len(channel_names):
                selected_channels.append(channel_names[choice - 1])
            else:
                print("Número fuera de rango. Inténtelo de nuevo.")
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número o 'done'.")
    return selected_channels


def listen_for_messages(stub, selected_channel, connection_state, stop_event, my_messages):
    while not stop_event.is_set():
        connection_state.wait_for_connection()
        print(f"\nListening for messages on channel {selected_channel}\n")
        print("\nPress any key to continue...\n")
        try:
            for message in stub.Subscribe(pubsub_pb2.Channel(name=selected_channel)):
                if message.content != "Alive":
                    my_messages.put(f"Received message on channel '{selected_channel}': {message.content}")
                if stop_event.is_set():
                    break
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.CANCELLED:
                print(f"Channel Closed!")


def send_messages(stub, selected_channels, connection_state, stop_event, my_messages):
    while not stop_event.is_set():
        connection_state.wait_for_connection()  # Esperar a que la conexión esté disponible

        # Mostrar los mensajes que han sido enviados a los
        # canales suscritos
        print('\n')
        while not my_messages.empty():
            print(my_messages.get())
        print('\n\n')

        flag_to_val = 0
        while flag_to_val == 0:
            print("Canales disponibles para enviar mensajes:")
            for i, channel in enumerate(selected_channels):
                print(f"{i + 1}. {channel}")
    
            try:
                channel_index = int(input("Seleccione el canal para enviar el mensaje: ")) - 1
        
                if 0 <= channel_index < len(selected_channels):
                    flag_to_val = 1
                else:
                    print("Por favor, seleccione un índice válido.\n")
            except ValueError:
                print("Por favor, ingrese un número válido.\n")

        selected_channel = selected_channels[channel_index]

        input_text = input("Enter message to send: ")

        try:
            stub.Publish(pubsub_pb2.Message(channel=selected_channel, content=input_text))
            print("Message sent.")
        except grpc.RpcError as e:
            print(f"Failed to send message: {e}")


def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = pubsub_pb2_grpc.PubSubStub(channel)
    health_stub = pubsub_pb2_grpc.HealthStub(channel)
    connection_state = ConnectionState()
    stop_event = Event()
    reconnection_thread = Thread(target=check_connection, args=(health_stub, stop_event, connection_state))
    reconnection_thread.start()
    global my_messages
    listener_threads = []
    try:
        selected_channels = get_channel_selection(stub)

        for selected_channel in selected_channels:
            thread = Thread(target=listen_for_messages,
                            args=(stub, selected_channel, connection_state, stop_event, my_messages))
            thread.start()
            listener_threads.append(thread)

        send_messages(stub, selected_channels, connection_state, stop_event, my_messages)

    except grpc.RpcError as e:
        print(f"No se ha podido conectar con el servidor, verifique que se encuentre activo. {e.code()}")
    except KeyboardInterrupt:
        print("\nInterrupción del programa recibida. Cerrando...")

    finally:
        stop_event.set()
        reconnection_thread.join()
        for thread in listener_threads:
            thread.join()
        channel.close()


if __name__ == '__main__':
    run()
