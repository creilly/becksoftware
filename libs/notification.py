import os
from twilio.rest import Client

chris = '+41782121057'
patrick = '+491633681855'

twilio = '+14155238886'

bilters = [chris,patrick]

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']

def fmt_whatsapp(number):
    return 'whatsapp:{}'.format(number)

def send_notification(message):
    client = Client(account_sid, auth_token)
    for bilter in bilters:
        m = client.messages.create(
            body=message,
            from_=fmt_whatsapp(twilio),
            to=fmt_whatsapp(bilter)
        )

# import smtplib
# from email.message import EmailMessage

# host = 'christopher.reilly@epfl.ch'

# listeners = ['christopher.reilly@epfl.ch']

# def send_notification(body):
#     msg = EmailMessage()
#     msg.set_content(body)
#     msg['Subject'] = 'lab notification'
#     msg['From'] = host
#     s = smtplib.SMTP('localhost')
#     for listener in listeners:
#         msg['To'] = listener
#         s.send_message(msg)
#     s.quit()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='send message to BILTers')
    parser.add_argument('message',help='message to send')
    message = parser.parse_args().message
    print('sending notification: "{}"'.format(message))
    send_notification(message)
