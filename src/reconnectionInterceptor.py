import grpc
import time

from src import pubsub_pb2_grpc


class ReconnectInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, max_retries=5, initial_backoff=1.0, max_backoff=60.0):
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff

    def intercept_unary_unary(self, continuation, client_call_details, request):
        retries = 0
        backoff = self.initial_backoff
        while retries < self.max_retries:
            try:
                return continuation(client_call_details, request)
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:  # El servidor no está disponible
                    if retries < self.max_retries - 1:
                        print(f"Attempt {retries + 1}: Retrying in {backoff} seconds...")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)  # Incrementar el backoff exponencialmente
                        retries += 1
                    else:
                        print("Max retries reached, giving up.")
                        raise
                else:
                    print(f"An RPC error occurred: {e.code()}")
                    raise
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                raise
        return None  # Si todos los reintentos fallan, retorna None o levanta una excepción


def create_stub_with_interceptor():
    channel = grpc.insecure_channel('localhost:50051')
    interceptor = ReconnectInterceptor(max_retries=5)  # Puedes ajustar el número de reintentos aquí
    intercepted_channel = grpc.intercept_channel(channel, interceptor)
    stub = pubsub_pb2_grpc.PubSubStub(intercepted_channel)
    return stub
