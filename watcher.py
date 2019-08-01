# -*- coding: utf-8 -*-
import requests
import datetime
import urllib
import json
import sys
import time
import os

from settings import HOME_PATH, RECIEVER_EMAIL_LIST, WATCH_DATA
from django.utils.functional import cached_property
from mailer import Mailer

reload(sys)
sys.setdefaultencoding('utf-8')


class Doctor:
    DOCTOR_LIST_PATH = os.path.join(HOME_PATH, 'doctor_list.json')
    session = None
    session_data = {}
    authorized = False
    watch_doctor_ids = []
    auth_data = {}

    def __init__(self, watch_item):
        self.auth_data = watch_item['auth']
        self.watch_doctor_ids = watch_item['watch_doctor_ids']
        self.session = requests.session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Content-Type': 'application/json',
            'Host': 'vrach42.ru',
            'Origin': 'https://vrach42.ru',
            'Referer': 'https://vrach42.ru/login',
        })
        print 'init', datetime.datetime.now()
        print self.auth_data['surname'], self.auth_data['name'], self.auth_data['insurance_policy']

    @property
    def watch_doctor_list(self):
        """ Данные о врачах, которые нам важны """
        if self.watch_doctor_ids:
            watch_doctor_list = filter(lambda x: x['id_doctor'] in self.watch_doctor_ids, self.doctor_list)
            for doctor in watch_doctor_list:
                doctor['tickets'] = self.get_tickets(doctor)
                doctor['opened_tickets'] = {}  # Открытые талоны для записи
                for ticket in doctor['tickets']:
                    opened_list = filter(lambda x: not x['is_closed'], ticket['timeSlots'])  # открытое для записи
                    if opened_list:
                        doctor['opened_tickets'][ticket['value']] = opened_list
            return watch_doctor_list
        return []

    def get_tickets(self, doctor_item):
        """ Получить записи к врачу"""
        if not doctor_item['tickets_cnt']:
            return []
        if not self.authorized:
            self.authorize()

        start = datetime.date.today()
        end = start + datetime.timedelta(days=90)
        doctor_params = {
            'id_hospital': 'bece99bb-9d2a-49f9-bded-8c9b56acc773',
            'id_hospital_type': '1',
            'id_doctor': doctor_item['id_doctor'],
            'id_specialty': doctor_item['id_specialty'],
            'begin_date': start.strftime('%Y-%m-%d'),
            'end_date': end.strftime('%Y-%m-%d')
        }
        url = 'https://vrach42.ru/v1/tickets?' + urllib.urlencode(doctor_params, doseq=True)
        response = self.session.get(url)
        return response.json()

    def authorize(self):
        """ авторизоваться """
        if 'session_id' in self.session_data:
            return

        response = self.session.post('https://vrach42.ru/v1/patients/state/check', json=self.auth_data)  # авторизация
        response = response.json()
        if 'session_id' in response:
            self.session_data = response  # lname, fname, area, session_id
            self.session.headers.update({'X-Patient-Session': self.session_data['session_id']})
            self.authorized = True
            print u'Успешно авторизованы'
            return True
        else:
            self.session_data = response  # ['details']['message']
            self.authorized = False
            return False

    def is_actual(self, on_time):
        """ Актуальна ли информация на выбранное время """
        return on_time > (datetime.datetime.now() - datetime.timedelta(hours=3))

    @cached_property
    def doctor_list(self):
        """ получить список врачей """

        # Если есть инфа в файле и она актуальна, то берём оттуда
        if os.path.exists(self.DOCTOR_LIST_PATH):
            timestamp = os.path.getmtime(self.DOCTOR_LIST_PATH)
            create_time = datetime.datetime.fromtimestamp(timestamp)
            if self.is_actual(create_time):
                with open(self.DOCTOR_LIST_PATH, "r") as read_file:
                    return json.load(read_file)

        # Берём с сайта данные
        self.authorize()
        if self.authorized:
            response = self.session.get('https://vrach42.ru/v1/doctors')
            doctor_list = response.json()
            if isinstance(doctor_list, list):
                self.save_doctor_list(doctor_list)
                return doctor_list
        else:
            print u'Warning: Мы не авторизовались и список врачей пуст'
        return []

    def save_doctor_list(self, doctor_list):
        if doctor_list:
            with open(self.DOCTOR_LIST_PATH, 'w') as f:
                json.dump(doctor_list, f)
            print u'Список врачей сохранён'

    def send_doctor_list_to_email(self, doctor_list):
        """ Отправить весь список докторов на почту """
        if doctor_list:
            context = dict(doctor_list=doctor_list)
            Mailer().send_html(RECIEVER_EMAIL_LIST, u'Обстановка на "Врач42"', context, 'template.jinja2')

    def one_loop(self):
        """ Один цикл работы программы """
        open_doctors = filter(lambda x: x['tickets_cnt'], self.watch_doctor_list)  # Докторы, у которых открылась запись
        if open_doctors:
            print u'Есть открытые записи.'
            self.send_doctor_list_to_email(open_doctors)
        else:
            print u'Запись к необходимым врачам ещё закрыта.'
        print 'done.\n'

    def loop(self, hours=3):
        """ Запустить цикл каждые hours часов """
        seconds = 60 * 60 * hours  # часы в секунды
        while True:
            self.one_loop()
            time.sleep(seconds)  # in seconds


# Для каждого полиса сделаем проверку
for watch_item in WATCH_DATA:
    doc = Doctor(watch_item)
    doc.one_loop()
    # doc.loop(hours=3)