import ipaddress

from django.db import models
from django.core.exceptions import ValidationError

from .lookups import IpIn
from .lookups import IpContains


class IPNetworkField(models.Field):
    description = 'A Django database field that is compatible with IPv4 and IPv6 and supports CIDR.'

    def db_type(self, connection):
        return 'char(150)'

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip()
        try:
            return ipaddress.ip_network(value, strict=False)
        except ValueError as error:
            raise ValidationError(error)

    def from_db_value(self, value, expression, connection):
        prefix = value[:4]
        value = value[4:-1]    # remove prefix and %
        if prefix == 'IPv4':
            max_length = ipaddress.IPV4LENGTH
        else:
            max_length = ipaddress.IPV6LENGTH
        string_ip = ipaddress.ip_address(int(value + '0' * (max_length-len(value)), 2)).__str__()
        string_network = string_ip + '/{}'.format(len(value))
        return ipaddress.ip_network(string_network)

    def get_prep_value(self, value):
        try:
            value = self.to_python(value)
        except ValidationError:
            return None
        if isinstance(value, ipaddress.IPv4Network):
            max_length = ipaddress.IPV4LENGTH
            prefix = 'IPv4'
        elif isinstance(value, ipaddress.IPv6Network):
            max_length = ipaddress.IPV6LENGTH
            prefix = 'IPv6'
        else:
            return str(value)
        bin_ip = str(bin(int(value.network_address)))[2:]
        bin_ip = '0' * (max_length - len(bin_ip)) + bin_ip
        bin_network = prefix + bin_ip[:value.prefixlen] + '%'
        return bin_network

    def get_prep_lookup(self, lookup_type, value):
        return self.get_prep_value(value)

    def get_lookup(self, lookup_name):
        if lookup_name == 'contains' or lookup_name == 'icontains':
            return IpContains
        elif lookup_name == 'in':
            return IpIn
        return super().get_lookup(lookup_name)