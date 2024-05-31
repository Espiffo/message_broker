import logging
import signal
from concurrent import futures
from time import sleep
import grpc
import pubsub_pb2
import pubsub_pb2_grpc
import threading
from threading import Event
import queue

import sys
server_stopped = False
stop_event = Event()


class HealthServicer(pubsub_pb2_grpc.HealthServicer):
    def Ping(self, request, context):
        return pubsub_pb2.Pong(message="pong")


class PubSubService(pubsub_pb2_grpc.PubSubServicer):

    def __init__(self):
        # Crea una lista con tres canales predefinidos a los
        # cuales los clientes se pueden suscribir
        self.channels = [pubsub_pb2.Channel(name="test"),
                         pubsub_pb2.Channel(name="channel2"),
                         pubsub_pb2.Channel(name="channel3")]

        self.channel_messages = {channel.name: queue.Queue(maxsize=100) for channel in
                                 self.channels}  # Diccionario para mapear las colas de mensajes
        self.subscribers = {channel.name: [] for channel in
                            self.channels}  # Diccionario para los suscriptores de cada canal
        self.locks = {channel.name: threading.Lock() for channel in
                      self.channels}  # Diccionario para el lock de cada canal
        self.semaphores = {channel.name: threading.Semaphore(100) for channel in
                           self.channels}  # Diccionario para el semáforo de cada canal
        self.interuptions_lock = threading.Lock()
        logging.info("PubSubService initialized.")

        with open("log.txt", 'w') as file:
            file.write('Server started. Listening on port 50051.')

    def _get_lock(self, channel):  # Obtener el lock para un canal
        return self.locks[channel]

    def _get_semaphore(self, channel):  # Obtener el semáforo para un canal
        return self.semaphores[channel]

    def _get_interuptions_lock(self):  # Obtener el semáforo para un canal
        return self.interuptions_lock        

    def Subscribe(self, request, context):
        alive_flag = 0
        subscriber_id = context.peer()  # Obtener un identificador único para el suscriptor
        channel = request.name
        if channel not in self.channel_messages:
            return
        lock = self._get_lock(channel)
        semaphore = self._get_semaphore(channel)

        with lock:
            self.subscribers[channel].append(subscriber_id)
            logging.info(f"Subscriber added to channel {channel}. ID: {subscriber_id}")

            lock_interuptions = self._get_interuptions_lock()
            with lock_interuptions:
                with open("log.txt", 'a') as file:
                    file.write(f"Subscriber added to channel {channel}. ID: {subscriber_id} \n\n")

        try:
            while True:
                with lock:
                    message_queue = self.channel_messages[channel]
                    if message_queue.empty():
                        alive_flag = alive_flag + 1
                        if alive_flag == 5:
                            yield pubsub_pb2.Message(channel=channel, content="Alive")
                            alive_flag = 0
                        continue
                    publisher_id, msg = message_queue.get()  # Obtener mensaje de la cola del canal
                    semaphore.release()  # Liberar un espacio en el semáforo
                if publisher_id != subscriber_id:  # Excluir al publicador

                    lock_interuptions = self._get_interuptions_lock()
                    with lock_interuptions:
                        with open("log.txt", 'a') as file:
                            file.write(
                                f"Messeage send to channel {channel}, for  subscriber of ID: {subscriber_id} \n\n")

                    yield pubsub_pb2.Message(channel=channel, content=msg)
                else:
                    # Volver a poner el mensaje si es del mismo publicador
                    with lock:
                        message_queue.put_nowait((publisher_id, msg))
                        semaphore.acquire()  # Volver a ocupar un espacio en el semáforo
        finally:
            with lock:
                if subscriber_id in self.subscribers[channel]:
                    lock_interuptions = self._get_interuptions_lock()
                    with lock_interuptions:
                        with open("log.txt", 'a') as file:
                            file.write(f"Subscriber removed from channel {channel}. ID: {subscriber_id} \n\n")

                    self.subscribers[channel].remove(subscriber_id)
                logging.info(f"Subscriber removed from channel {channel}. ID: {subscriber_id}")

    def Publish(self, request, context):
        publisher_id = context.peer()  # Obtener un identificador único para el publicador
        channel = request.channel
        if channel not in self.channel_messages:
            return pubsub_pb2.Ack(success=False)
        lock = self._get_lock(channel)
        semaphore = self._get_semaphore(channel)
        if publisher_id not in self.subscribers[channel]:
            self.Subscribe(request, context)
        semaphore.acquire()  # Esperar hasta que haya espacio en la cola --1

        with lock:
            message_queue = self.channel_messages[channel]
            message_queue.put((publisher_id, request.content))  # Publicar mensaje con ID del publicador
            logging.info(f"Published message to channel {request.channel}.")

            lock_interuptions = self._get_interuptions_lock()
            with lock_interuptions:
                with open("log.txt", 'a') as file:
                    file.write(f"Published message to channel {request.channel}, by {publisher_id} \n\n")

            return pubsub_pb2.Ack(success=True)

    def ListChannels(self, request, context):
        return pubsub_pb2.ChannelList(channels=self.channels)


server = grpc.server(futures.ThreadPoolExecutor(max_workers=200))


def signal_handler(signal, frame):
    global server_stopped
    global server

    if not server_stopped:
        print('\nRecibiendo señal de parada, cerrando el servidor...')
        server_stopped = True
        stop_event.set()
        server.stop(5)
        
        # Terminate all threads
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                if thread.is_alive():
                    if thread.name != "Thread-1 (_serve)":
                        print(f"\n-{thread.name}- was communicating with SERVER")
                        # thread.terminate()
                        print("\033[93mWARNING:\033[0m Terminating communication with ", end="")
                        print(f"-{thread.name}-")
                else:
                    thread.join()
    sys.exit(0)

# Configurar el manejo de señales

signal.signal(signal.SIGINT, signal_handler)

signal.signal(signal.SIGTERM, signal_handler)


def serve():
    logging.basicConfig(level=logging.INFO)
    pubsub_pb2_grpc.add_PubSubServicer_to_server(PubSubService(), server)
    pubsub_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info("Server started. Listening on port 50051.")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print('Detenido por interrupción del teclado')
        server.stop(5)
    finally:
        server.stop(5)
        # Asegurarse de llamar stop() también aquí para limpieza
        print('\nPress [Ctrl+C] to kill the server.')
        return 0


if __name__ == '__main__':
    serve()
