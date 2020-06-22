import providers
import socket

class Source(providers.DataSource):
    def required_args(self):
        return ['batadv_dev', 'domain_code', 'known_codes']

    def call(self, batadv_dev, domain_code, known_codes):
        try:
            return socket.gethostname() + '-' + known_codes[batadv_dev]
        except KeyError:
            return socket.gethostname() + '-' + domain_code

