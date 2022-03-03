# import dotenv from python
import os, sys
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

@app.command("/analyze")
def user_leave_prediction_analyze(ack, respond, command):
    ack()
    try:
        if command['text'] == '':
            raise Exception('Command is empty!')
        info = helper.command_info_extrator(command='analyze', msg=command, app=app)
        if info['uid'] is None:
            raise Exception('User not found!')
        else:
            response = modelGen.modelTrain(userid=info['uid'], test=True)
            respond(response['msg'])
    except:
        # print(sys.exc_info())
        respond(f"Error: Invalid command format! Try /analyze @username")

@app.command("/test")
def user_leave_prediction(ack, respond, command):
    ack()
    try:
        if command['text'] == '':
            raise Exception('Command is empty!')
        info = helper.command_info_extrator(command='analyze', msg=command, app=app)
        if info.uid is None:
            raise Exception('User not found!')
        else:
            time_pred = helper.time_range_validation(info.time_interval)
            if time_pred['res']:
                response = modelGen.modelTrain(userid=info.uid, time_gap=info.time_interval)
                respond(response['msg'])
            else:
                respond(f"Error: {time_pred['msg']}")
    except:
        respond(f"Error: Invalid command format! Try /test @user_name time_interval")


# @app.command("/help")
# def help(ack, respond, command):
#     ack()
#     respond(f"Commands:\n/refresh_db - Refresh database with latest messages\n/test @<name> <time_interval> - Predict the user's activity in the given time interval")

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
