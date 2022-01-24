# import dotenv from python
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from HelperFunc import HelperFunc
from pymongo import MongoClient

load_dotenv()

# slack app
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
# mongo client
client = MongoClient(os.getenv("MONGO_URI"))
db = client.afk_db
# helper function
helper = HelperFunc()

@app.event("message")
def handle_message_events(body, logger):
    msg = {
        'text':body['event']['text'], 
        'user': body['event']['user'], 
        'ts': body['event']['ts']
        }
    helper.insert_single(msg, db)

@app.command("/refresh_db")
def save_messages(ack, respond, command):
    ack()
    helper.refresh_db(app, os.getenv("SLACK_CHANNEL_ID"), db)
    respond(f"Database refreshed!")

@app.command("/test")
def user_leave_prediction(ack, respond, command):
    ack()
    name = command['text'].split(' ')[0].replace('@', '')
    time_interval = command['text'].split(' ')[1]
    uid = helper.name_userid(name, app)
    if uid is None:
        respond(f"Error: Invalid user!")
    else:
        time_pred = helper.time_range_validation(time_interval)
        if time_pred['res']:
            respond(f"Error: {time_pred['msg']}")
        else:
            # TODO: Add a individual prediciton run.
            pass
        

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
