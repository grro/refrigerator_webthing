from webthing import (SingleThing, Property, Thing, Value, WebThingServer)
import sys
import logging
import tornado.ioloop
from refrigerator import Refrigerator




class RefrigeratorThing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, refrigerator: Refrigerator):
        Thing.__init__(
            self,
            'urn:dev:ops:refrigerator-1',
            'RefrigeratorSwitch',
            ['MultiLevelSensor'],
            description
        )
        self.ioloop = tornado.ioloop.IOLoop.current()
        self.refrigerator = refrigerator
        self.refrigerator.set_listener(self.on_value_changed)

        self.is_on = Value(self.refrigerator.is_on())
        self.add_property(
            Property(self,
                     'on',
                     self.is_on,
                     metadata={
                         'title': 'on',
                         "type": "boolean",
                         'description': 'true, if on)',
                         'readOnly': True,
                     }))

        self.last_activation_time = Value(refrigerator.last_activation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.add_property(
            Property(self,
                     'last_activation_time',
                     self.last_activation_time,
                     metadata={
                         'title': 'last_activation_time',
                         "type": "string",
                         'description': 'last activation time (ISO 8601)',
                         'readOnly': True,
                     }))

    
        self.last_deactivation_time = Value(refrigerator.last_deactivation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.add_property(
            Property(self,
                     'last_deactivation_time',
                     self.last_deactivation_time,
                     metadata={
                         'title': 'last_deactivation_time',
                         "type": "string",
                         'description': 'last deactivation time (ISO 8601)',
                         'readOnly': True,
                     }))

        self.refrigerator_hours_today = Value(self.refrigerator.refrigerator_hours_today)
        self.add_property(
            Property(self,
                     'refrigerator_hours_today',
                     self.refrigerator_hours_today,
                     metadata={
                         'title': 'refrigerator_hours_today',
                         "type": "integer",
                         'description': 'hours today active',
                         'readOnly': True,
                     }))

        self.refrigerator_hours_current_year = Value(self.refrigerator.refrigerator_hours_current_year)
        self.add_property(
            Property(self,
                     'refrigerator_hours_current_year',
                     self.refrigerator_hours_current_year,
                     metadata={
                         'title': 'refrigerator_hours_current_year',
                         "type": "integer",
                         'description': 'hours current year active',
                         'readOnly': True,
                     }))

        self.refrigerator_hours_estimated_year = Value(self.refrigerator.refrigerator_hours_estimated_year)
        self.add_property(
            Property(self,
                     'refrigerator_hours_estimated_year',
                     self.refrigerator_hours_estimated_year,
                     metadata={
                         'title': 'refrigerator_hours_estimated_year',
                         "type": "integer",
                         'description': 'hours estimated year active',
                         'readOnly': True,
                     }))

    def on_value_changed(self):
        self.ioloop.add_callback(self._on_value_changed)

    def _on_value_changed(self):
        self.is_on.notify_of_external_update(self.refrigerator.is_on())
        self.last_activation_time.notify_of_external_update(self.refrigerator.last_activation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.last_deactivation_time.notify_of_external_update(self.refrigerator.last_deactivation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.refrigerator_hours_today.notify_of_external_update(self.refrigerator.refrigerator_hours_today)
        self.refrigerator_hours_current_year.notify_of_external_update(self.refrigerator.refrigerator_hours_current_year)
        self.refrigerator_hours_estimated_year.notify_of_external_update(self.refrigerator.refrigerator_hours_estimated_year)


def run_server(description: str, port: int, addr: str, directory: str):
    refrigerator = Refrigerator(addr, directory)
    server = WebThingServer(SingleThing(RefrigeratorThing(description, refrigerator)), port=port, disable_host_validation=True)
    try:
        logging.info('starting the server http://localhost:' + str(port) + " (addr=" + addr + ")")
        refrigerator.start()
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        refrigerator.stop()
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('tornado.access').setLevel(logging.ERROR)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    run_server("description", int(sys.argv[1]), sys.argv[2], sys.argv[3])
