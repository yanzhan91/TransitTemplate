import logging
from flask import Flask, render_template
from flask_ask import Ask, statement, question, context, session
import re
import CheckBusIntent
import SetBusIntent
import GetBusIntent
import os


app = Flask(__name__)
ask = Ask(app, '/')
logger = logging.getLogger()


@ask.launch
def launch():
    welcome_text = render_template('welcome')
    return question(welcome_text)\
        .simple_card('Welcome to %s' % os.environ['project_name'], remove_html(welcome_text))\
        .reprompt(render_template('help'))


@ask.intent('AMAZON.HelpIntent')
def help():
    return question(render_template('help')).simple_card('AustinTransit Help', render_template('help_card'))


@ask.intent('AMAZON.StopIntent')
def stop():
    return statement('ok')


@ask.intent('CheckBusIntent')
def check_bus_intent(bus_id, stop_id):
    session.attributes['request'] = 'check_bus'

    result = analyze_id(bus_id, 'bus')
    if result:
        session.attributes['current_param'] = 0
        return result
    result = analyze_id(stop_id, 'stop')
    if result:
        session.attributes['current_param'] = 1
        return result

    bus_minutes_message = check_bus(session.attributes['bus'], session.attributes['stop'])
    return generate_statement_card(bus_minutes_message, 'Check Bus Status')


@ask.intent('SetBusIntent')
def set_bus_intent(bus_id, stop_id, preset_id):
    session.attributes['request'] = 'set_bus'

    result = analyze_id(bus_id, 'bus')
    if result:
        session.attributes['current_param'] = 0
        return result
    result = analyze_id(stop_id, 'stop')
    if result:
        session.attributes['current_param'] = 1
        return result
    result = analyze_id(preset_id, 'preset')
    if result:
        session.attributes['current_param'] = 2
        return result

    set_bus_success_message = \
        set_bus(session.attributes['bus'], session.attributes['stop'], session.attributes['preset'])
    return generate_statement_card(set_bus_success_message, 'Set Bus Status')


@ask.intent('GetBusIntent')
def get_bus_intent(preset_id):
    session.attributes['request'] = 'get_bus'

    if not preset_id:
        preset_id = '1'

    result = analyze_id(preset_id, 'preset')
    if result:
        session.attributes['current_param'] = 0
        return result

    get_bus_message = get_bus(session.attributes['preset'])
    print(get_bus_message)
    return generate_statement_card(get_bus_message, 'Get Bus Status')


@ask.intent('AnswerIntent')
def answer_intent(num):
    if check_iteration():
        return statement(render_template('try_again_message'))

    if 'request' not in session.attributes:
        return get_bus_intent('1')
    current_param = session.attributes['current_param']
    if session.attributes['request'] == 'check_bus':
        return check_bus_intent(assign_params(current_param, 0, num), assign_params(current_param, 1, num))
    elif session.attributes['request'] == 'set_bus':
        return set_bus_intent(
            assign_params(current_param, 0, num),
            assign_params(current_param, 1, num),
            assign_params(current_param, 2, num))
    elif session.attributes['request'] == 'get_bus':
        return get_bus_intent(assign_params(current_param, 0, num))
    else:
        return question(render_template('try_again_message')).reprompt(render_template('try_again_message'))


def assign_params(current_param, param_num, num):
    return num if current_param == param_num else None


def analyze_id(num, num_type):
    if num_type in session.attributes:
        return None
    if not num or not re.compile('\\d+').match(str(num)):
        return question(render_template('%s-question' % num_type))\
            .reprompt(render_template('%s-question-reprompt' % num_type))
    else:
        session.attributes[num_type] = num
        return None


def check_bus(bus_id, stop_id):
    logger.info('Checking Bus %s at %s...' % (bus_id, stop_id))
    minutes, stpnm = CheckBusIntent.check_bus(bus_id, stop_id)

    if stpnm:
        stpnm = stpnm.replace('&', 'and')

    logging.info('Minutes received: %s' % minutes)
    if len(minutes) == 0:
        return render_template('no_bus_message', bus_id=bus_id, stop_id=stop_id, stop_name=stpnm)
    minute_strings = []
    for minute in minutes:
        minute_strings.append('%s minutes away <break time="200ms"/>' % minute)
    minute_string = ' and '.join(minute_strings)

    response = render_template('bus_minutes_message', bus_id=bus_id, stop_id=stop_id,
                               minutes=minute_string, stop_name=stpnm)

    return response


def set_bus(bus_id, stop_id, preset):
    logger.info('Setting Bus %s at %s for preset %s...' % (bus_id, stop_id, preset))
    try:
        SetBusIntent.set_bus(context.System.user.userId, bus_id, stop_id, preset)
    except Exception as e:
        logger.error(e)
        return render_template('internal_error_message')
    logger.info('Set bus %s at %s was successful' % (bus_id, stop_id))
    set_bus_success_message = render_template('set_bus_success_message', bus_id=bus_id, stop_id=stop_id, preset=preset)
    return set_bus_success_message


def get_bus(preset):
    logger.info('Getting Bus at preset %s...' % preset)
    try:
        bus_id, stop_id = GetBusIntent.get_bus(context.System.user.userId, preset)
        logger.info('Bus retrieved was %s at %s' % (bus_id, stop_id))
        if not bus_id or not stop_id:
            return render_template('preset_not_found_message', preset=preset)
        return check_bus(bus_id, stop_id)
    except Exception as e:
        logger.error(e)
        return render_template('internal_error_message')


def generate_statement_card(speech, title):
    return statement(speech).simple_card(title, remove_html(speech))


def remove_html(text):
    return re.sub('<[^<]*?>|\\n', '', text)


def check_iteration():
    if 'iter' not in session.attributes:
        session.attributes['iter'] = 1
        return False
    if session.attributes['iter'] > 2:
        return True
    session.attributes['iter'] += 1


if __name__ == '__main__':
    app.config['ASK_VERIFY_REQUESTS'] = False
    app.run()
