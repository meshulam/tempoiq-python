import warnings
import exceptions
from selection import Selection, ScalarSelector, OrClause, AndClause
from selection import Compound, DictSelectable
from functions import *
from tempoiq.protocol import Rule
from tempoiq.tempo_exceptions import TempoIQDeprecationWarning


PIPEMSG = 'Pipeline functions passed to monitor call currently have no effect'
DEVICEMSG = 'Pipeline functions passed to device reads have no effect'
ROLLUPMSG = 'Rollup, find, and multi-rollup must have a start and end passed to them'
DELETEMSG = 'Deleting data from sensors requires a start and end time'
DELETEKEYMSG = 'Deleting data from a sensor requires a selection specifying one device key and one sensor key only'
DELETEDEVICEMSG = 'Start and end are invalid arguments for deleting devices.  Are you sure you didn\'t mean session.query(Sensor).delete() instead?'
LATESTMSG = 'The latest() method has been deprecated. Please use single("latest") instead.'


def extract_key_for_monitoring(selection):
    if hasattr(selection.selection, 'selectors'):
        if len(selection.selection.selectors) > 1:
            msg = 'monitoring rules may only be read out by one key at a time'
            raise ValueError(msg)
        return selection.selection.selectors[0].value
    else:
        return selection.selection.value


class QueryBuilder(object):
    """Class to build queries. All instance methods in this class return
    the instance itself. This allows you to construct queries fluently,
    by chaining method calls."""

    def __init__(self, client, object_type):
        self.client = client
        self.object_type = object_type.__name__.lower() + 's'
        self.selection = {
            'devices': Selection(),
            'sensors': Selection(),
            'rules': Selection()
        }
        self.pipeline = []
        self.operation = None

    def _handle_monitor_read(self, **kwargs):
        key = extract_key_for_monitoring(self.selection['rules'])
        method_name = kwargs['__method$$']
        method = getattr(self.client.monitoring_client, method_name)
        return method(key)

    def _normalize_pipeline_functions(self, start, end):
        for function in self.pipeline:
            if isinstance(function, (Rollup, MultiRollup, Find)):
                if start is None or end is None:
                    raise ValueError(ROLLUPMSG)
                if function.args[-1] is None:
                    function.args[-1] = start
            elif isinstance(function, Interpolation):
                if function.args[-2] is None:
                    function.args[-2] = start
                if function.args[-1] is None:
                    function.args[-1] = end

    def _validate_datapoint_delete(self):
        if issubclass(self.selection['devices'].selection.__class__,
                      (Compound, DictSelectable)):
            raise ValueError(DELETEKEYMSG)
        if issubclass(self.selection['sensors'].selection.__class__,
                      (Compound, DictSelectable)):
            raise ValueError(DELETEKEYMSG)
        if self.selection['devices'].selection is None:
            raise ValueError(DELETEKEYMSG)
        if self.selection['sensors'].selection is None:
            raise ValueError(DELETEKEYMSG)
        return (self.selection['devices'].selection.value,
                self.selection['sensors'].selection.value)

    def aggregate(self, function):
        """Aggregate the data in the query with the specified aggregation
        function"""
        self.pipeline.append(Aggregation(function))
        return self

    def annotations(self):
        if not isinstance(self.object_type, Rule):
            raise TypeError('Annotations only applies to monitoring rules')
        key = extract_key_for_monitoring(self.selection['rules'])
        return self.client.monitoring_client.get_annotations(key)

    def changes(self):
        if not isinstance(self.object_type, Rule):
            raise TypeError('Changes only applies to monitoring rules')
        key = extract_key_for_monitoring(self.selection['rules'])
        return self.client.monitoring_client.get_changelog(key)

    def convert_timezone(self, tz):
        """Convert the result's data points to the specified time zone.

        :param String tz: Time zone"""
        self.pipeline.append(ConvertTZ(tz))
        return self

    def delete(self, **kwargs):
        """Execute an API call to delete the objects that are a result of this
        query. Currently only supported for deleting entire devices.
        equivalent to passing this QueryBuilder to
        :meth:`tempoiq.client.Client.delete_device`"""
        if self.object_type == 'devices':
            start = kwargs.get('start')
            end = kwargs.get('end')
            if start or end:
                raise ValueError(DELETEDEVICEMSG)

            self.operation = APIOperation('find', {'quantifier': 'all'})
            return self.client.delete_device(self)
        elif self.object_type == 'sensors':
            start = kwargs.get('start')
            end = kwargs.get('end')
            if start is None or end is None:
                raise ValueError(DELETEMSG)
            (device_key, sensor_key) = self._validate_datapoint_delete()
            args = {'start': start, 'stop': end, 'device_key': device_key,
                    'sensor_key': sensor_key}
            self.operation = APIOperation('delete', args)
            r = self.client.delete_from_sensors(device_key, sensor_key,
                                                start, end)
            return r
        elif self.object_type == 'rules':
            key = extract_key_for_monitoring(self.selection['rules'])
            return self.client.monitoring_client.delete_rule(key)

    def filter(self, selector):
        """Filter the query based on the provided selector. The argument may be
        a :class:`~tempoiq.protocol.query.selection.ScalarSelector` or the
        result of combining several selectors
        with :func:`~tempoiq.protocol.query.selection.or_` or
        :func:`~tempoiq.protocol.query.selection.and_`\ .

        :param selector:
        """
        if not isinstance(selector, (ScalarSelector, OrClause, AndClause)):
            raise TypeError('Invalid object for filter: "%s"' % selector)
        self.selection[selector.selection_type].add(selector)
        return self

    def find(self, function, period, start=None):
        self.pipeline.append(Find(function, period, start))
        return self

    def interpolate(self, function, period, start=None, end=None):
        """Interpolate the sensor data

        :param String function: Interpolation function ("zoh" or "linear")
        :param String period: Time period to interpolate"""
        self.pipeline.append(Interpolation(function, period))
        return self

    def logs(self):
        if not isinstance(self.object_type, Rule):
            raise TypeError('Logs only applies to monitoring rules')
        key = extract_key_for_monitoring(self.selection['rules'])
        return self.client.monitoring_client.get_logs(key)

    def monitor(self, rule):
        if self.pipeline:
            warnings.warn(PIPEMSG, exceptions.FutureWarning)
        rule.selection = self.selection
        return self.client.monitor(rule)

    def multi_rollup(self, functions, period, start=None):
        """Apply multiple rollups to the same sensor data.

        :param list functions: list of rollup functions to apply
        :param String period: Time period of the rollups
        """
        self.pipeline.append(MultiRollup(functions, period, start))
        return self

    def rollup(self, function, period, start=None):
        """Apply a rollup function to the query.

        :param String function: The rollup function to apply
        :param String period: The time period of the rollup
        :param DateTime start: (optional) A timestamp to use as the start of
        the first rollup period. Default is the same as the start of the read.
        """
        self.pipeline.append(Rollup(function, period, start))
        return self

    def read(self, **kwargs):
        """Make the API call to the TempoIQ backend for this query.

        :param start: required when reading sensor data. Start of time range
                      to read.
        :type start: DateTime
        :param end: required when reading sensor data. End of time range to
                    read.
        :type end: DateTime
        """
        if self.object_type == 'sensors':
            start = kwargs['start']
            end = kwargs['end']
            args = {'start': start, 'stop': end}
            #this is set here to be used by the encoder to correctly specify
            #the last step of the operation in the JSON
            self.operation = APIOperation('read', args)
            self._normalize_pipeline_functions(start, end)
            return self.client.read(self)
        elif self.object_type == 'devices':
            if self.pipeline:
                self.pipeline = []
                warnings.warn(DEVICEMSG, exceptions.FutureWarning)
            self.operation = APIOperation('find',
                                          {'quantifier': 'all'})
            return self.client.search_devices(self)
        elif self.object_type == 'rules':
            kwargs['__method$$'] = 'get_rule'
            return self._handle_monitor_read(**kwargs)
        else:
            msg = 'Only sensors, devices, and rules can be selected'
            raise TypeError(msg)

    def single(self, function, timestamp=None, include_selection=False):
        """Make a single-point API call to the TempoIQ backend for this query.

        :param String function: Method for finding the point to return for
                    each sensor. Ex: earliest, latest, before, after
        :param DateTime timestamp: required for all functions except earliest
        """
        if self.object_type == 'sensors':
            args = {'include_selection': include_selection,
                    'function': function}
            if timestamp is not None:
                args['timestamp'] = timestamp

            self.operation = APIOperation('single', args)
            return(self.client.single(self))
        else:
            msg = 'Single value only applies to sensors'
            raise TypeError(msg)

    def latest(self, include_selection=False):
        """Deprecated. Use the
        :func:`~tempoiq.protocol.query.builder.QueryBuilder.single` call
        instead."""
        warnings.warn(LATESTMSG, TempoIQDeprecationWarning)
        self.single('latest', include_selection=include_selection)

    def usage(self):
        if not isinstance(self.object_type, Rule):
            raise TypeError('Usage only applies to monitoring rules')
        key = extract_key_for_monitoring(self.selection['rules'])
        return self.client.monitoring_client.get_usage(key)
