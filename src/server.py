import logging
import signal
import time
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
        self.channels = [pubsub_pb2.Channel(name="test"),
                         pubsub_pb2.Channel(name="channel2"),
                         pubsub_pb2.Channel(name="channel3")]

        # A thread safe queue for every channel
        self.channel_messages = {channel.name: queue.Queue(maxsize=10) for channel in self.channels}

        # Dictionary to keep a list of subscribers for every channel
        self.subscribers = {channel.name: [] for channel in self.channels}

        # lock to protect the operations over the log file
        self.file_lock = threading.Lock()

        logging.info("PubSubService initialized.")
        with open("log.txt", 'w') as file:
            file.write('Server started. Listening on port 50051.')

    def _get_file_lock(self):
        return self.file_lock

    def Subscribe(self, request, context):
        subscriber_id = context.peer()
        channel = request.name
        if channel not in self.channel_messages:
            return

        with threading.Lock():  # Protect access to subscribers list
            self.subscribers[channel].append(subscriber_id)
            logging.info(f"Subscriber added to channel {channel}. ID: {subscriber_id}")
            with self._get_file_lock():
                with open("log.txt", 'a') as file:
                    file.write(f"Subscriber added to channel {channel}. ID: {subscriber_id}\n")

        try:
            while True:
                message_queue = self.channel_messages[channel]
                start_time = time.time()

                while time.time() - start_time < 5:
                    if not message_queue.empty():
                        break
                    sleep(1)  # Check every second if a message is available

                if message_queue.empty():
                    yield pubsub_pb2.Message(channel=channel, content="Alive") # Send an alive signal

                else:
                    publisher_id, msg = message_queue.get()
                    if publisher_id != subscriber_id:
                        with self._get_file_lock():
                            with open("log.txt", 'a') as file:
                                file.write(f"Message sent to channel {channel}, for subscriber ID: {subscriber_id}\n")
                        yield pubsub_pb2.Message(channel=channel, content=msg)
                    else:
                        message_queue.put_nowait((publisher_id, msg))

        finally:
            with threading.Lock():  # Protect access to subscribers list
                if subscriber_id in self.subscribers[channel]:
                    self.subscribers[channel].remove(subscriber_id)
                    logging.info(f"Subscriber removed from channel {channel}. ID: {subscriber_id}")
                    with self._get_file_lock():
                        with open("log.txt", 'a') as file:
                            file.write(f"Subscriber removed from channel {channel}. ID: {subscriber_id}\n")

    def Publish(self, request, context):
        publisher_id = context.peer()
        channel = request.channel
        if channel not in self.channel_messages:
            return pubsub_pb2.Ack(success=False)

        if publisher_id not in self.subscribers[channel]:
            self.Subscribe(request, context)

        message_queue = self.channel_messages[channel]
        if message_queue.full():
            return pubsub_pb2.Ack(success=False)

        message_queue.put((publisher_id, request.content))
        logging.info(f"Published message to channel {request.channel}.")
        with self._get_file_lock():
            with open("log.txt", 'a') as file:
                file.write(f"Published message to channel {request.channel}, by {publisher_id}\n")

        return pubsub_pb2.Ack(success=True)

    def ListChannels(self, request, context):
        return pubsub_pb2.ChannelList(channels=self.channels)


server = grpc.server(futures.ThreadPoolExecutor(max_workers=200))


def signal_handler(signal, frame):
    global server_stopped
    global server

    if not server_stopped:
        print('\nReceived stop signal, shutting down server...')
        server_stopped = True
        stop_event.set()
        server.stop(5)

        for thread in threading.enumerate():
            if thread != threading.current_thread():
                if thread.is_alive():
                    print(f"Terminating thread {thread.name}")
                    thread.join()
    sys.exit(0)


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
        print('Stopped by keyboard interruption')
        server.stop(5)
    finally:
        server.stop(5)
        print('\nPress [Ctrl+C] to kill the server.')


if __name__ == '__main__':
    serve()
