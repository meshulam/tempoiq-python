import json
from protocol.cursor import DeviceCursor, StreamResponseCursor
from protocol.cursor import DataPointsCursor
from protocol.decoder import TempoIQDecoder


SUCCESS = 0
FAILURE = 1
PARTIAL = 2


class ResponseException(Exception):
    """Exception class for HTTP responses"""

    def __init__(self, response):
        self.response = response
        self.msg = 'TempoIQ response returned status: %d' % response.status

    def __repr__(self):
        return self.msg

    def __str__(self):
        return self.msg


class Response(object):
    """Represents responses from the TempoIQ API.  The Response object has
    several useful attributes after it is created:

        * successful: whether the overall request was successful (see below)
        * status: the HTTP status code for the API call
        * reason: the explanation for the HTTP status code
        * data: an object or list of objects representing the data from the API
        * error: a string if the API returned any additional error information
                 in the response body, None otherwise

    **Note:** data will be None if the status code was anything other than
    200.

    **Note:** successful has 3 possible values defined as constants in this
    module, SUCCESS, FAILURE, and PARTIAL.  A PARTIAL value can occur during a
    multi-write if some datapoints fail to write.  The error attribute in that
    case will be a JSON encoded string of errors for each datapoint.  The
    response object does *not* derserialize that error (there could be other
    circumstances where the error is not JSON encoded), so if that case, error
    handling code surrounding multi-writes should decode the error attribute
    with the json library if it wants to attempt error recovery.

    :param obj resp: a response object from the requests library"""

    def __init__(self, resp, session):
        self.resp = resp
        self.session = session
        self.status = resp.status_code
        self.status_code = self.status
        self.reason = resp.reason
        if self.status == 200:
            self.successful = SUCCESS
            self.error = None
        elif self.status == 207:
            self.successful = PARTIAL
            self.error = self.resp.text
        else:
            self.successful = FAILURE
            self.error = self.resp.text

        self.resp.encoding = "UTF-8"
        self.body = self.resp.text
        self.data = None


class WriteResponse(Response):
    def __init__(self, resp, session):
        self.resp = resp
        self.session = session
        self.status = resp.status_code
        self.status_code = self.status
        self.reason = resp.reason

        self.resp.encoding = "UTF-8"
        self.body = self.resp.text
        self.data = None
        self._cached_status = None
        if self.status_code < 299:
            self.parse(self.body)

    def parse(self, body):
        if not self.body:
            self.body = '{}'
        self.data = json.loads(self.body)

    @property
    def successful(self):
        if self._cached_status is not None:
            return self._cached_status
        elif not self.data:
            return False
        else:
            failures = 0
            devices = len(self.data)
            status = None
            for k in self.data:
                if self.data[k]['success'] is False:
                    failures += 1
            if failures == devices:
                status = FAILURE
            elif failures > 0:
                status = PARTIAL
            else:
                status = SUCCESS
            self._cached_status = status
            return status

    @property
    def failures(self):
        if not self.data:
            raise StopIteration
        for k in self.data:
            if self.data[k]['success'] is False:
                yield (k, self.data[k]['message'])

    def _filter_by(self, device_state):
        if not self.data:
            raise StopIteration
        for k in self.data:
            if self.data[k]['device_state'] == device_state:
                yield k

    @property
    def created(self):
        return self._filter_by('created')

    @property
    def existing(self):
        return self._filter_by('existing')

    @property
    def modified(self):
        return self._filter_by('modified')


class DeviceResponse(Response):
    def __init__(self, resp, session, fetcher):
        super(DeviceResponse, self).__init__(resp, session)
        self.fetcher = fetcher
        if self.successful == SUCCESS:
            self.parse(self.body)

    def parse(self, body):
        data = json.loads(body)
        self.data = DeviceCursor(self, data, self.fetcher)


class SensorPointsResponse(Response):
    def __init__(self, resp, session, fetcher):
        super(SensorPointsResponse, self).__init__(resp, session)
        self.fetcher = fetcher
        if self.successful == SUCCESS:
            self.parse(self.body)

    def parse(self, body):
        self.data = DataPointsCursor(self, json.loads(body), self.fetcher)


class StreamResponse(Response):
    def __init__(self, resp, session, fetcher):
        super(StreamResponse, self).__init__(resp, session)
        self.fetcher = fetcher
        if self.successful == SUCCESS:
            self.parse(self.body)

    def parse(self, body):
        self.data = StreamResponseCursor(self, json.loads(body), self.fetcher)


class MonitoringResponse(Response):
    def __init__(self, resp, session, decoder_method=None):
        super(MonitoringResponse, self).__init__(resp, session)
        self.decoder_method = decoder_method
        if self.successful == SUCCESS and self.body != '':
            self.parse(self.body)
        else:
            self.data = None

    def parse(self, body):
        decoder = TempoIQDecoder()
        if self.decoder_method is not None:
            decoder.decoder = getattr(decoder, self.decoder_method)

        self.data = json.loads(body, object_hook=decoder)


class AlertListResponse(MonitoringResponse):
    def __init__(self, resp, session):
        super(AlertListResponse, self).__init__(resp, session,
                                                'decode_alert_list')

    def parse(self, body):
        decoder = TempoIQDecoder()
        if self.decoder_method is not None:
            decoder.decoder = getattr(decoder, self.decoder_method)

        self.data = json.loads(body, object_hook=decoder)


class DeleteDatapointsResponse(Response):
    def __init__(self, resp, session):
        super(DeleteDatapointsResponse, self).__init__(resp, session)
        self.parse(self.body)

    def parse(self, body):
        self.data = {}
