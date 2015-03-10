import json
import urlparse
import urllib
from protocol.encoder import WriteEncoder, CreateEncoder, ReadEncoder
from protocol.query.builder import QueryBuilder
from response import *
from endpoint import media_type, media_types


def escape(s):
    return urllib.quote(s, safe='')


def make_fetcher(endpoint, url, headers={}):
    def fetcher(cursor):
        resp = endpoint.get(url, json.dumps(cursor), headers=headers)
        if resp.status_code != 200:
            #munge this so the ResponsException can work with it
            resp.status = resp.status_code
            raise ResponseException(resp)
        return json.loads(resp.text)
    return fetcher


class MonitoringClient(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def delete_rule(self, key):
        url = urlparse.urljoin(self.endpoint.base_url, 'monitors/' + key)
        resp = self.endpoint.delete(url)
        return Response(resp, self.endpoint)

    def get_alert(self, key, alert_id):
        url1 = urlparse.urljoin(self.endpoint.base_url,
                                'monitors/' + key + '/')
        url = urlparse.urljoin(url1, 'alerts/' + str(alert_id))
        resp = self.endpoint.get(url)
        return MonitoringResponse(resp, self.endpoint, 'decode_alert')

    def get_annotations(self, key):
        url = urlparse.urljoin(self.endpoint.base_url,
                               'monitors/annotations/' + key)
        resp = self.endpoint.get(url)
        return Response(resp, self.endpoint)

    def get_changelog(self, key):
        url = urlparse.urljoin(self.endpoint.base_url,
                               'monitors/%s/changes/' % key)
        resp = self.endpoint.get(url)
        return Response(resp, self.endpoint)

    def get_logs(self, key):
        url = urlparse.urljoin(self.endpoint.base_url,
                               'monitors/%s/logs/' % key)
        resp = self.endpoint.get(url)
        return MonitoringResponse(resp, self.endpoint, 'decode_rule_logs')

    def get_rule(self, key):
        url = urlparse.urljoin(self.endpoint.base_url, 'monitors/' + key)
        return MonitoringResponse(self.endpoint.get(url), self)

    def get_usage(self, key):
        url = urlparse.urljoin(self.endpoint.base_url,
                               'monitors/%s/usage/' % key)
        resp = self.endpoint.get(url)
        return MonitoringResponse(resp, self.endpoint, 'decode_rule_usage')

    def list_alerts(self, key):
        url1 = urlparse.urljoin(self.endpoint.base_url,
                                'monitors/' + key + '/')
        url = urlparse.urljoin(url1, 'alerts/')
        resp = self.endpoint.get(url)
        return AlertListResponse(resp, self.endpoint)

    def list_rules(self):
        url = urlparse.urljoin(self.endpoint.base_url, 'monitors/')
        return MonitoringResponse(self.endpoint.get(url), self,
                                  'decode_rule_list')


class Client(object):
    """Entry point for all TempoIQ API calls.

    :param endpoint: backend and credentials to connect to
    :type endpoint: tempoiq.endpoint.HTTPEndpoint
    """

    write_encoder = WriteEncoder()
    create_encoder = CreateEncoder()
    read_encoder = ReadEncoder()

    def __init__(self, endpoint, read_version='v2'):
        self.endpoint = endpoint
        self.monitoring_client = MonitoringClient(self.endpoint)
        self.DATAPOINT_ACCEPT_TYPE = media_type('datapoint-collection',
                                                read_version)
        self.ERROR_ACCEPT_TYPE = media_type('error', 'v1')
        self.DEVICE_ACCEPT_TYPE = media_type('device-collection', 'v2')
        self.QUERY_CONTENT_TYPE = media_type('query', 'v1')
        self.read_version = read_version

    def create_device(self, device):
        """Create a new device

        :param device:
        :type device: :class:`~tempoiq.protocol.device.Device`
        :rtype: :class:`tempoiq.response.Response` with a
                :class:`tempoiq.protocol.device.Device` data payload"""

        url = urlparse.urljoin(self.endpoint.base_url, 'devices/')
        j = json.dumps(device, default=self.create_encoder.default)
        resp = self.endpoint.post(url, j)
        return Response(resp, self.endpoint)

    def delete_device(self, query):
        """Delete devices that match the provided query.

        :param query:
        :type query: :class:`tempoiq.protocol.query.builder.QueryBuilder`
        :rtype: :class:`tempoiq.response.Response`"""

        url = urlparse.urljoin(self.endpoint.base_url, 'devices/')
        j = json.dumps(query, default=self.read_encoder.default)
        resp = self.endpoint.delete(url, j)
        return Response(resp, self.endpoint)

    def update_device(self, device):
        """Update the attributes of a device.

        :param device:
        :type device: :class:`~tempoiq.protocol.device.Device`
        :rtype: :class:`tempoiq.response.Response` with a
                :class:`tempoiq.protocol.device.Device` data payload"""

        path = '/'.join(['devices', escape(device.key)])
        url = urlparse.urljoin(self.endpoint.base_url, path)
        j = json.dumps(device, default=self.create_encoder.default)
        resp = self.endpoint.put(url, j)
        return Response(resp, self.endpoint)

    def delete_from_sensors(self, device_key, sensor_key, start, end):
        path = '/'.join(
            ['devices', escape(device_key), 'sensors',  escape(sensor_key),
             'datapoints'])
        url = urlparse.urljoin(self.endpoint.base_url, path)
        j = json.dumps({'start': start.isoformat(),
                        'stop': end.isoformat()})
        resp = self.endpoint.delete(url, j)
        return DeleteDatapointsResponse(resp, self.endpoint)

    def monitor(self, rule):
        url = urlparse.urljoin(self.endpoint.base_url, 'monitors/')
        rule_json = json.dumps(rule, default=self.write_encoder.default)
        resp = self.endpoint.post(url, rule_json)
        return MonitoringResponse(resp, self.endpoint)

    def query(self, object_type):
        """Begin to build a query on the given object type.

        :param object_type: Either :class:`~tempoiq.protocol.device.Device`
                            or :class:`~tempoiq.protocol.sensor.Sensor`
        :rtype: :class:`~tempoiq.protocol.query.builder.QueryBuilder`"""

        return QueryBuilder(self, object_type)

    def read(self, query):
        url = urlparse.urljoin(self.endpoint.base_url, 'read/')
        j = json.dumps(query, default=self.read_encoder.default)
        accept_headers = [self.ERROR_ACCEPT_TYPE, self.DATAPOINT_ACCEPT_TYPE]
        content_header = self.QUERY_CONTENT_TYPE
        headers = media_types(accept_headers, content_header)
        resp = self.endpoint.get(url, j, headers=headers)
        fetcher = make_fetcher(self.endpoint, url, headers)
        if self.read_version == 'v2':
            return SensorPointsResponse(resp, self.endpoint, fetcher)
        else:
            return StreamResponse(resp, self.endpoint, fetcher)

    def search_devices(self, query):
        #TODO - actually use the size param
        url = urlparse.urljoin(self.endpoint.base_url, 'devices/')
        j = json.dumps(query, default=self.read_encoder.default)
        accept_headers = [self.ERROR_ACCEPT_TYPE, self.DEVICE_ACCEPT_TYPE]
        content_header = self.QUERY_CONTENT_TYPE
        headers = media_types(accept_headers, content_header)
        fetcher = make_fetcher(self.endpoint, url, headers)
        return DeviceResponse(self.endpoint.get(url, j, headers=headers),
                              self.endpoint, fetcher)

    def single(self, query):
        url = urlparse.urljoin(self.endpoint.base_url, 'single/')
        j = json.dumps(query, default=self.read_encoder.default)
        fetcher = make_fetcher(self.endpoint, url)
        return SensorPointsResponse(self.endpoint.get(url, j), self.endpoint,
                                    fetcher)

    def update_rule(self, rule):
        route = 'monitors/%s' % rule.key
        url = urlparse.urljoin(self.endpoint.base_url, route)
        rule_json = json.dumps(rule, default=self.write_encoder.default)
        resp = self.endpoint.put(url, rule_json)
        return MonitoringResponse(resp, self.endpoint)

    def write(self, write_request):
        """Write data points to one or more devices and sensors.

        The write_request argument is a dict which maps device keys to device
        data.

        The device data is itself a dict mapping sensor key to a list of
        :class:`tempoiq.protocol.point.Point`

        :param dict write_request:"""

        url = urlparse.urljoin(self.endpoint.base_url, 'write/')
        default = self.write_encoder.default
        resp = self.endpoint.post(url, json.dumps(write_request,
                                                  default=default))
        return WriteResponse(resp, self.endpoint)
