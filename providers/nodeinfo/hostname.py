import providers
import socket

class Source(providers.DataSource):
    def required_args(self):
        return ['batadv_dev']
    def call(self, batadv_dev):
        return socket.gethostname() + '-' + batadv_dev[3:]
