from __future__ import division
from __future__ import print_function
import smtplib
import base64
import datetime
from jinja2 import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httplib2
import os
from apiclient import discovery
from oauth2client.client import GoogleCredentials
from oauth2client import tools
from oauth2client import client
from oauth2client.file import Storage

SCOPES = 'https://mail.google.com/'
CLIENT_SECRET_FILE = 'credentials.json'
APPLICATION_NAME = 'Mlbdb'


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = './credentials-stored.json'

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def send_email(current, previous, totals, settings):
    view_object = {
        'current': current,
        'previous': previous,
        'totals': totals,
        'settings': settings,
    }
    with open(settings['email_template'], 'r') as f:
        template = Template(f.read())

    ready_view = _elaborate_view(view_object)
    email_contents = template.render(view=ready_view)

    with open('email.html', 'w') as h:
       h.write(email_contents)
    # _send_mail(ready_view['subject'], email_contents, settings['email_to'],
    #            settings['email_from'], settings['email_password'], settings['email_cc'])


def _elaborate_view(view_object):
    today = datetime.date.today()
    view_object['date'] = today.strftime('%Y-%m-%d')
    view_object['subject'] = 'MLB Updates - {}'.format(view_object['date'])
    view_object['num_games'] = len(view_object['current'])
    view_object['num_actionable'] = 0
    for game in view_object['current']:
        if game.action['bet'] == 'home' or game.action['bet'] == 'away':
            view_object['num_actionable'] += 1

    # summarize our last days results
    if view_object['previous']:
        date_key = view_object['previous'][0].date.strftime('%Y-%m-%d')
        if date_key in view_object['totals']:
            view_object['last'] = view_object['totals'][date_key]
            view_object['last']['net'] = int(view_object['last']['net']  * 100) / 100
        else:
            view_object['last'] = None
    view_object['week_net'] = 0
    view_object['week_count'] = 0
    view_object['week_correct'] = 0
    view_object['extended_net'] = 0
    view_object['extended_count'] = 0
    view_object['extended_correct'] = 0
    for i in range(0, 100):
        date_key = (today + datetime.timedelta(days=-i)).strftime('%Y-%m-%d')
        if date_key in view_object['totals']:
            if i < 7:
                view_object['week_net'] += view_object['totals'][date_key]['net']
                view_object['week_count'] += view_object['totals'][date_key]['bet']
                view_object['week_correct'] += view_object['totals'][date_key]['correct']
            view_object['extended_net'] += view_object['totals'][date_key]['net']
            view_object['extended_count'] += view_object['totals'][date_key]['bet']
            view_object['extended_correct'] += view_object['totals'][date_key]['correct']
    view_object['week_net'] = int(view_object['week_net']  * 100) / 100
    view_object['extended_net'] = int(view_object['extended_net']  * 100) / 100
    
    for game in view_object['current']:
        if game.home_odds:
            game.home_odds['minimum_confidence'] = int(game.home_odds['minimum_confidence'] * 10000) / 100 
        if game.away_odds:
            game.away_odds['minimum_confidence'] = int(game.away_odds['minimum_confidence'] * 10000) / 100 
        if game.prediction:
            game.prediction['home_wins'] = int(game.prediction['home_wins'] * 10000) / 100
            game.prediction['away_wins'] = int(game.prediction['away_wins'] * 10000) / 100
    for game in view_object['previous']:
        if game.home_odds:
            game.home_odds['minimum_confidence'] = int(game.home_odds['minimum_confidence'] * 10000) / 100 
        if game.away_odds:
            game.away_odds['minimum_confidence'] = int(game.away_odds['minimum_confidence'] * 10000) / 100 
        if game.prediction:
            game.prediction['home_wins'] = int(game.prediction['home_wins'] * 10000) / 100
            game.prediction['away_wins'] = int(game.prediction['away_wins'] * 10000) / 100

    return view_object


def _send_mail(subject, string_body, to, sender, password, cc_list):
    msg = MIMEMultipart('alternative')
    msg['To'] = to
    msg['From'] = sender
    msg['Cc'] = ','.join(cc_list)
    msg['subject'] = subject
    msg.attach(MIMEText(string_body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [to], msg.as_string())
        server.quit()
    except Exception as e:
        msg = {'raw': base64.urlsafe_b64encode(msg.as_string())}
        credentials = get_credentials()
        service = discovery.build('gmail', 'v1', credentials=credentials)
        send_message(service, sender, msg)


def send_message(service, user_id, message_in):
    """Send an email message.

    Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.

    Returns:
    Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message_in).execute())
        print ('Message Id: %s' % message['id'])
        return message
    except Exception as e:
        print ('An error occurred: %s' % e)

