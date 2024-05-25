import logging
import signal
from concurrent import futures
import grpc
import pubsub_pb2
import pubsub_pb2_grpc
import threading
import queue


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

    def Publish(self, request, context):
        publisher_id = context.peer()  # Obtener un identificador único para el publicador
        channel = request.channel
        if channel not in self.channel_messages:
            return pubsub_pb2.Ack(success=False)
        lock = self._get_lock(channel)
        semaphore = self._get_semaphore(channel)

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

    def Subscribe(self, request, context):
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

    def ListChannels(self, request, context):
        return pubsub_pb2.ChannelList(channels=self.channels)


server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))


def signal_handler(signal, frame):
    print('Recibiendo señal de parada, cerrando el servidor...')
    server.stop(10)  # Proporciona 10 segundos de gracia para que los threads terminen


# Configurar el manejo de señales
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def serve():
    logging.basicConfig(level=logging.INFO)
    pubsub_pb2_grpc.add_PubSubServicer_to_server(PubSubService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info("Server started. Listening on port 50051.")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print('Detenido por interrupción del teclado')
    finally:
        server.stop(10)  # Asegurarse de llamar stop() también aquí para limpieza
        print('Servidor cerrado correctamente.')


if __name__ == '__main__':
    serve()
