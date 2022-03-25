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
    # detects every message
    msg = {
        'text':body['event']['text'],
        'user': body['event']['user'],
        'ts': body['event']['ts']
        }
    helper.insert_single(msg)

@app.command("/refresh_db")
def save_messages(ack, respond, command):
    # Command to refresh db
    ack()
    helper.refresh_db(app)
    respond(f"Database refreshed!")

@app.command("/predict")
def user_leave_prediction(ack, respond, command):
    # Command to predict pattenrs in user leaves
    ack()
    # try:
        # Check if command is empty
    if command['text'] == '':
        raise Exception('Command is empty!')
    # Extract information from the command
    info = helper.command_info_extrator(msg=command, app=app)
    # Validate user_id
    if info['uid'] is None:
        raise Exception('User not found!')
    else:
        # Validate provided time_range then start main prediction code
        # time_pred = helper.time_range_validation(info['time_interval'])
        # if time_pred['status']:
        response = modelGen.modelTrain(userid=info['uid'])
        # else:
        #     response = {'msg': time_pred['msg'], 'status':False}
    # except:
    #     # print the raised exception
    #     print(sys.exc_info())
    #     response = {'msg': 'Error: Invalid command format! Try /predict @username', 'status':False}
    respond(response['msg'])


# @app.command("/help")
# def help(ack, respond, command):
#     ack()
#     respond(f"Commands:\n/refresh_db - Refresh database with latest messages\n/test @<name> <time_interval> - Predict the user's activity in the given time interval")

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
