from webthing import (SingleThing, Property, Thing, Value, WebThingServer)
import sys
import logging
import tornado.ioloop
from switch import Switch




class SwitchThing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, switch: Switch):
        Thing.__init__(
            self,
            'urn:dev:ops:switch-1',
            switch.name + 'Switch',
            ['MultiLevelSensor'],
            description
        )
        self.ioloop = tornado.ioloop.IOLoop.current()
        self.switch = switch
        self.switch.set_listener(self.on_value_changed)

        self.is_on = Value(self.switch.is_on(), self.switch.set_on)
        self.add_property(
            Property(self,
                     'on',
                     self.is_on,
                     metadata={
                         'title': 'on',
                         "type": "boolean",
                         'description': 'true, if on)',
                         'readOnly': False,
                     }))

        self.power = Value(self.switch.power)
        self.add_property(
            Property(self,
                     'power',
                     self.power,
                     metadata={
                         'title': 'power',
                         "type": "integer",
                         'description': 'the current power consumption)',
                         'readOnly': True,
                     }))

        self.last_activation_time = Value(switch.last_activation_time.strftime("%Y-%m-%dT%H:%M:%S"))
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

    
        self.last_deactivation_time = Value(switch.last_deactivation_time.strftime("%Y-%m-%dT%H:%M:%S"))
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

        self.hours_today = Value(self.switch.hours_today)
        self.add_property(
            Property(self,
                     'hours_today',
                     self.hours_today,
                     metadata={
                         'title': 'hours_today',
                         "type": "integer",
                         'description': 'hours today active',
                         'readOnly': True,
                     }))

    def on_value_changed(self):
        self.ioloop.add_callback(self._on_value_changed)

    def _on_value_changed(self):
        self.is_on.notify_of_external_update(self.switch.is_on())
        self.last_activation_time.notify_of_external_update(self.switch.last_activation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.last_deactivation_time.notify_of_external_update(self.switch.last_deactivation_time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.hours_today.notify_of_external_update(self.switch.hours_today)
        self.power.notify_of_external_update(self.switch.power)


def run_server(description: str, port: int, name: str, addr: str, directory: str):
    switch = Switch(name, addr, directory)
    server = WebThingServer(SingleThing(SwitchThing(description, switch)), port=port, disable_host_validation=True)
    try:
        logging.info('starting the server http://localhost:' + str(port) + " (addr=" + addr + ")")
        switch.start()
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        switch.stop()
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('tornado.access').setLevel(logging.ERROR)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    run_server("description", int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
