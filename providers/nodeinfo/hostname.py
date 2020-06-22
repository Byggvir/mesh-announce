import providers
import socket

class Source(providers.DataSource):
    def required_args(self):
        return ['batadv_dev']

    def call(self, batadv_dev):
        try:
            return socket.gethostname() + '-d' + batadv_dev[3:]
        except:
            return socket.gethostname()

