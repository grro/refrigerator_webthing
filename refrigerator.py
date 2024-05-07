from requests import Session
from datetime import datetime
from typing import Optional, List, Tuple
from threading import Thread
from redzoo.database.simple import SimpleDB
from redzoo.math.display import duration
from time import sleep
import logging



class Shelly1:

    def __init__(self, addr: str):
        self.__session = Session()
        self.addr = addr

    def query(self) -> Tuple[bool, int, List[int]]:
        uri = self.addr + '/status'
        try:
            resp = self.__session.get(uri, timeout=10)
            try:
                data = resp.json()
                on = data['relays'][0]['ison']
                power = data['meters'][0]['power']
                counters = data['meters'][0]['counters']
                return on, power, counters
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



class Refrigerator:

    def __init__(self, addr: str, directory: str):
        self.__is_running = True
        self.__listener = lambda: None    # "empty" listener
        self.__shelly = Shelly1(addr)
        self.__is_on = False
        self.__cooling_secs_per_day = SimpleDB("refrigerator_" + str(id), sync_period_sec=60, directory=directory)
        self.last_activation_time = datetime.now()
        self.last_deactivation_time = datetime.now()
        self.__sync()

    def set_listener(self, listener):
        self.__listener = listener

    def start(self):
        Thread(target=self.__measure, daemon=True).start()

    def stop(self):
        self.__is_running = False

    def is_on(self) -> bool:
        return self.__is_on

    def set_on(self, on: bool):
        self.__update_last_activity(self.is_on(), on)
        if on:
            if self.__is_on is False:
                self.__shelly.switch(True)
                self.__is_on = True
                logging.debug("Refrigerator activated")
        else:
            if self.__is_on is True:
                self.__shelly.switch(False)
                self.__is_on = False
                cooling_time = (datetime.now() - self.last_activation_time)
                day = datetime.now().strftime('%j')
                self.__cooling_secs_per_day.put(day, self.__cooling_secs_per_day.get(day, 0) + cooling_time.total_seconds(), ttl_sec=366*24*60*60)
                logging.debug(self.__str__() + " deactivated (heating time " + duration(cooling_time.total_seconds(), 1) + ")")
        self.__sync()


    def __update_last_activity(self, old_on: bool, new_old: bool):
        if new_old:
            if old_on is False:
                self.last_activation_time = datetime.now()
        else:
            if old_on is True:
                self.last_deactivation_time = datetime.now()


    def cooling_secs_per_day(self, day_of_year: int) -> Optional[int]:
        secs = self.__cooling_secs_per_day.get(str(day_of_year), -1)
        if secs > 0:
            return secs
        else:
            return None

    def __refrigerator_hours_per_day(self, day_of_year: int) -> int:
        heater_secs_today = self.__cooling_secs_per_day.get(str(day_of_year))
        if heater_secs_today is None:
            return 0
        else:
            return heater_secs_today / (60*60)

    @property
    def refrigerator_hours_today(self) -> int:
        today = int(datetime.now().strftime('%j'))
        return self.__refrigerator_hours_per_day(today)

    def __refrigerator_hours_list_current_year(self) -> List[int]:
        current_day = int(datetime.now().strftime('%j'))
        hours_per_day = [self.__refrigerator_hours_per_day(day_of_year) for day_of_year in range(0, current_day + 1)]
        return [hours for hours in hours_per_day if hours is not None]

    @property
    def refrigerator_hours_current_year(self) -> int:
        return sum(self.__refrigerator_hours_list_current_year())

    @property
    def refrigerator_hours_estimated_year(self) -> int:
        hours_per_day = self.__refrigerator_hours_list_current_year()
        if len(hours_per_day) > 0:
            return int(sum(hours_per_day) * 365 / len(hours_per_day))
        else:
            return 0

    def __sync(self):
        is_on, power, counters = self.__shelly.query()
        self.__update_last_activity(self.is_on(), is_on)
        self.__is_on = is_on
        self.__listener()

    def __measure(self):
        while self.__is_running:
            try:
                self.__sync()
            except Exception as e:
                logging.warning("error occurred on sync " + str(e))
            sleep(5)