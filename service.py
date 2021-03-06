# -*- coding: utf-8 -*-

"""
Main function
"""
# pylint: disable=invalid-name

import time
import os
import smtplib
import jinja2
import json

from rtmapi import Rtm
from mailer import Mailer
from mailer import Message
from operator import attrgetter

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def retrieve_tasks():
    print("Running job")
    # with open("config.yaml", 'r') as stream:
    #     cfg = yaml.load(stream)
    with open('event.json') as data_file:
        cfg = json.load(data_file)

    api_key = cfg['rtm_api_key']
    shared_secret = cfg['rtm_shared_secret']
    token = cfg['rtm_token']

    api = Rtm(api_key, shared_secret, "delete", token)

    # authenication block, see http://www.rememberthemilk.com/services/api/authentication.rtm
    # check for valid token
    if not api.token_valid():
        print("got an invalid token", api)
        return

    # get all open tasks, see
    # http://www.rememberthemilk.com/services/api/methods/rtm.tasks.getList.rtm

    yesterdays_list = api.rtm.tasks.getList(filter="completed:yesterday")
    yesterdays = []
    for tasklist in yesterdays_list.tasks:
        for taskseries in tasklist:
            print(taskseries.task.due, taskseries.name)
            yesterdays.append(taskseries)

    # for 3am tasks, may be an issue if it runs during the day
    yesterdays_extended_list = api.rtm.tasks.getList(filter="completed:today")
    for tasklist in yesterdays_extended_list.tasks:
        for taskseries in tasklist:
            print(taskseries.task.due, taskseries.name)
            yesterdays.append(taskseries)

    todays_list = api.rtm.tasks.getList(filter="dueBefore:tomorrow")
    todays = []
    for tasklist in todays_list.tasks:
        for taskseries in tasklist:
            if taskseries.task.completed == "":
                print(taskseries.task.due, taskseries.name)
                todays.append(taskseries)

    process_tasks(todays, yesterdays)


def process_tasks(todays, yesterdays):
    print("Todays: ", todays)
    print("Yesterdays: ", yesterdays)
    sorted_todays = tag_sort(todays)
    sorted_yesterdays = tag_sort(yesterdays)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Andrew's Tasks [{0}]".format(time.strftime("%a, %b %d"))
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('')
    )
    template = env.get_template('email.html')
    html = template.render(todays=sorted_todays, yesterdays=sorted_yesterdays)

    part = MIMEText(html, 'html')
    msg.attach(part)

    send_message(msg)
    # Send the message via local SMTP server.

def send_message(msg):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()

    with open('event.json') as data_file:
        cfg = json.load(data_file)

    houston_mail = cfg['houston_mail']
    houston_password = cfg['houston_password']
    target_emails = cfg['target_emails']

    server.login(houston_mail, houston_password)

    for email in target_emails:
        server.sendmail(houston_mail, email, msg.as_string())

    server.quit()
    print("Sent messages!")

def tag_sort(taskseries_list):
    for x in taskseries_list:
        for tag in x.tags:  # use iterator for RTM object
            x.tag = tag.value

        if x.tag == 'thought':
            x.color_hex = "8700fb"
        elif x.tag == 'core':
            x.color_hex = "3561ff"
        elif x.tag == 'platform':
            x.color_hex = "36d659"
        elif x.tag == 'networking':
            x.color_hex = "830048"
        elif x.tag == 'social':
            x.color_hex = "b4a300"
        else:
            x.color_hex = "201c1c"

        if x.tag is None:
            x.tag = "general"
            x.color_hex = "201c1c"
    return sorted(taskseries_list, key=attrgetter('tag'))


def handler(event, context):
    print("Got handler")
    retrieve_tasks()
    return

# retrieve_tasks()
