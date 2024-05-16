from requests import Session
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple
from threading import Thread
from redzoo.database.simple import SimpleDB
from redzoo.math.display import duration
from time import sleep
import logging


class ShellySwitch(ABC):

    @abstractmethod
    def supports(self) -> bool:
        pass

    @abstractmethod
    def query(self) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def switch(self, on: bool):
        pass

    @abstractmethod
    def close(self):
        pass



class Shelly1(ShellySwitch):

    def __init__(self, addr: str):
        self.__session = Session()
        self.addr = addr

    def close(self):
        self.__session.close()

    def supports(self) -> bool:
        uri = self.addr + '/status'
        try:
            resp = self.__session.get(uri, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            self.__renew_session()
            raise e

    def query(self) -> Tuple[bool, int]:
        uri = self.addr + '/status'
        try:
            resp = self.__session.get(uri, timeout=10)
            try:
                data = resp.json()
                on = data['relays'][0]['ison']
                power = data['meters'][0]['power']
                return on, power
            except Exception as e:
                raise Exception("called " + uri + " got " + str(resp.status_code) + " " + resp.text + " " + str(e))
        except Exception as e:
            self.__renew_session()
            raise e

    def switch(self, on: bool):
        uri = self.addr + '/relay/0?turn=' + ('on' if on else 'off')
        try:
            resp = self.__session.get(uri, timeout=10)
            if resp.status_code != 200:
                raise Exception("called " + uri + " got " + str(resp.status_code) + " " + resp.text)
        except Exception as e:
            self.__renew_session()
            raise Exception("called " + uri + " got " + str(e))

    def __renew_session(self):
        logging.info("renew session")
        try:
            self.__session.close()
        except Exception as e:
            logging.warning(str(e))
        self.__session = Session()


class ShellyPlus1(ShellySwitch):

    def __init__(self, addr: str):
        self.__session = Session()
        self.addr = addr

    def close(self):
        self.__session.close()

    def supports(self) -> bool:
        uri = self.addr + '/rpc/Switch.GetStatus?id=0'
        try:
            resp = self.__session.get(uri, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            self.__renew_session()
            raise e

    def query(self) -> Tuple[bool, int]:
        uri = self.addr + '/rpc/Switch.GetStatus?id=0'
        try:
            resp = self.__session.get(uri, timeout=10)
            try:
                data = resp.json()
                on = data['output']
                power = 0
                return on, power
            except Exception as e:
                raise Exception("called " + uri + " got " + str(resp.status_code) + " " + resp.text + " " + str(e))
        except Exception as e:
            self.__renew_session()
            raise e

    def switch(self, on: bool):
        uri = self.addr + '/rpc/Switch.Set?id=0&on=' + ('true' if on else 'false')
        try:
            resp = self.__session.get(uri, timeout=10)
            if resp.status_code != 200:
                raise Exception("called " + uri + " got " + str(resp.status_code) + " " + resp.text)
        except Exception as e:
            self.__renew_session()
            raise Exception("called " + uri + " got " + str(e))

    def __renew_session(self):
        logging.info("renew session")
        try:
            self.__session.close()
        except Exception as e:
            logging.warning(str(e))
        self.__session = Session()



class Switch:

    def __init__(self, name: str, addr: str, directory: str):
        self.__is_running = True
        self.__listener = lambda: None    # "empty" listener
        self.name = name
        # auto select
        self.__shelly = Shelly1(addr)
        if not self.__shelly.supports():
            self.__shelly.close()
            self.__shelly = ShellyPlus1(addr)
        self.__is_on = False
        self.__power = 0
        self.__active_secs_per_day = SimpleDB("switch" + Switch.__escape(addr), sync_period_sec=60, directory=directory)
        self.last_activation_time = datetime.now()
        self.last_deactivation_time = datetime.now()
        self.__sync()

    @staticmethod
    def __escape(text: str) -> str:
        return text.lower().replace("http", "").replace("://", "").replace(":", "_").replace("/", "").replace(".", "_")

    def set_listener(self, listener):
        self.__listener = listener

    def start(self):
        Thread(target=self.__measure, daemon=True).start()

    def stop(self):
        self.__is_running = False

    @property
    def power(self) -> int:
        return self.__power

    def is_on(self) -> bool:
        return self.__is_on

    def set_on(self, on: bool):
        self.__update_last_activity(self.is_on(), on)
        if on:
            if self.__is_on is False:
                self.__shelly.switch(True)
                self.__is_on = True
                logging.info(self.name + " activated")
        else:
            if self.__is_on is True:
                self.__shelly.switch(False)
                self.__is_on = False
                cooling_time = (datetime.now() - self.last_activation_time)
                day = datetime.now().strftime('%j')
                self.__active_secs_per_day.put(day, self.__active_secs_per_day.get(day, 0) + cooling_time.total_seconds(), ttl_sec=366 * 24 * 60 * 60)
                logging.info(self.name + " deactivated (activation time " + duration(cooling_time.total_seconds(), 1) + ")")
        self.__sync()


    def __update_last_activity(self, old_on: bool, new_old: bool):
        if new_old:
            if old_on is False:
                self.last_activation_time = datetime.now()
        else:
            if old_on is True:
                self.last_deactivation_time = datetime.now()

    def active_secs_per_day(self, day_of_year: int) -> Optional[int]:
        secs = self.__active_secs_per_day.get(str(day_of_year), -1)
        if secs > 0:
            return secs
        else:
            return None

    def __active_hours_per_day(self, day_of_year: int) -> int:
        heater_secs_today = self.__active_secs_per_day.get(str(day_of_year))
        if heater_secs_today is None:
            return 0
        else:
            return heater_secs_today / (60*60)

    @property
    def hours_today(self) -> int:
        today = int(datetime.now().strftime('%j'))
        return self.__active_hours_per_day(today)

    def __sync(self):
        is_on, power = self.__shelly.query()
        self.__update_last_activity(self.is_on(), is_on)
        self.__is_on = is_on
        self.__power = power
        self.__listener()

    def __measure(self):
        while self.__is_running:
            try:
                self.__sync()
            except Exception as e:
                logging.warning(self.name + " error occurred on sync " + str(e))
            sleep(3.3)