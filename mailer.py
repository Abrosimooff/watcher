# -*- coding: utf-8 -*-
import os
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from settings import WATCHER_EMAIL, WATCHER_PASSWORD, SMTP_IP, SMTP_PORT
from jinja2 import Template
from settings import HOME_PATH

class Mailer:
    """ Отпарвка email """

    def __init__(self):
        pass

    @staticmethod
    def _send(to_email, message_string):
        """ Отпарвить сформированное email-сообщение """
        server = smtplib.SMTP_SSL(SMTP_IP, SMTP_PORT)
        server.ehlo()
        server.login(WATCHER_EMAIL, WATCHER_PASSWORD)
        server.sendmail(WATCHER_EMAIL, to_email, message_string)
        server.close()

    def send_html(self, to_email, subject, context, template_path):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = WATCHER_EMAIL
        msg['To'] = to_email

        html = open(os.path.join(HOME_PATH, template_path)).read()
        template = Template(html.decode('utf8'))
        html = template.render(**context)

        part = MIMEText(html.encode('utf8'), 'html')
        msg.attach(part)
        self._send(to_email, msg.as_string())

    def send_text(self, to_email, subject, text):
        subject_base64 = base64.encodestring(subject.encode('utf8')).strip()
        subject = u" =?UTF-8?B?%s?=" % subject_base64
        message = u"""From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (WATCHER_EMAIL, u", ".join([to_email]), subject, text)
        self._send(to_email, message.encode('utf8'))