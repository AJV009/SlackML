# import dotenv from python
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from src.HelperFunc import HelperFunc
from src.ModelGen import ModelGen

load_dotenv()

# slack app
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
# helper function
helper = HelperFunc()
modelGen = ModelGen()

@app.event("message")
def handle_message_events(body, logger):
    msg = {
        'text':body['event']['text'], 
        'user': body['event']['user'], 
        'ts': body['event']['ts']
        }
    helper.insert_single(msg)

@app.command("/refresh_db")
def save_messages(ack, respond, command):
    ack()
    helper.refresh_db(app)
    respond(f"Database refreshed!")

@app.command("/test")
def user_leave_prediction(ack, respond, command):
    ack()
    # check if command['text'] is not empty
    try:
        if command['text'] == '':
            raise Exception('Command is empty!')
        command['text'] = command['text'].replace(u'\xa0', u' ')
        name = command['text'].split(' ')[0].replace('@', '')
        time_interval = command['text'].split(' ')[1]
        uid = helper.name_userid(name=name, app=app)
        if uid is None:
            raise Exception('User not found!')
        else:
            time_pred = helper.time_range_validation(time_interval)
            if time_pred['res']:
                response = modelGen.modelTrain(userid=uid, time_gap=time_interval)
                respond(response['msg'])
            else:
                respond(f"Error: {time_pred['msg']}")
    except:
        respond(f"Error: Invalid command format! Try /test @user_name time_interval")

@app.command("/analyze")
def user_leave_prediction_analyze(ack, respond, command):
    ack()
    try:
        if command['text'] == '':
            raise Exception('Command is empty!')
        command['text'] = command['text'].replace(u'\xa0', u' ')
        name = command['text'].split(' ')[0].replace('@', '')
        uid = helper.name_userid(name=name, app=app)
        if uid is None:
            raise Exception('User not found!')
        else:
            response = modelGen.modelAccTest(userid=uid)
            respond(response['msg'])
    except:
        respond(f"Error: Invalid command format! Try /analyze @user_name")


# @app.command("/help")
# def help(ack, respond, command):
#     ack()
#     respond(f"Commands:\n/refresh_db - Refresh database with latest messages\n/test @<name> <time_interval> - Predict the user's activity in the given time interval")

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
