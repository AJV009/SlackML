import os
from tabnanny import check
from slack_sdk.errors import SlackApiError
import pandas as pd
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

class HelperFunc:

    def __init__(self):
        # possible keywords, TODO: Replace with a NLP solution
        self.kw = [
            'afk', 
            'brb', 
            'will be back', 
            'taking rest',
            'away from keyboard', 
            'headache', 
            'not well', 
            'leaving for the day', 
            'not feeling well', 
            'Done for the day',
            'logging out',
            'Closing for today',
            'Leaving'
            ]
        self.ts = lambda x: datetime.datetime.fromtimestamp(float(x)).strftime('%Y-%m-%d %H:%M:%S')
        load_dotenv()
        client = MongoClient(os.getenv("MONGO_URI"))
        self.db = client.afk_db

    # Bin the time series
    def time_bin_binaryfy(self, df, time_col='ts', time_gap='1h'):
        temp_df = df.copy()
        temp_df.set_index(temp_df[time_col], inplace=True)
        temp_df.index = pd.to_datetime(temp_df.index)
        temp_df = temp_df.resample(time_gap).sum()
        return temp_df

    def user_filter(self, df, user=None):
        temp_df = df.copy()
        if user is not None:
            temp_df = temp_df[temp_df['user']==user]
        temp_df.drop(['user'], axis=1, inplace=True)
        return temp_df

    def model_data_prep(self, df, userid=None, time_col='ts', time_gap='1h'):
        prep_data = df.copy()
        prep_data = self.user_filter(df=prep_data, user=userid)
        prep_data = self.time_bin_binaryfy(df=prep_data, time_col=time_col, time_gap=time_gap)
        prep_data['ds'] = prep_data.index
        prep_data['y'] = prep_data['text']
        if '_id' in prep_data.columns:
            prep_data.drop(['_id'], axis=1, inplace=True)
        prep_data.drop(['text'], axis=1, inplace=True)
        prep_data.reset_index(drop=True, inplace=True)
        return prep_data

    # Refresh complete conversation history with DB and local CSV file
    def refresh_db(self, app):
        conversation_history = []
        try:
            cursor = '0'
            while (cursor != ''):
                result = app.client.conversations_history(
                    channel=os.getenv("SLACK_CHANNEL_ID"),
                    limit=70,
                    cursor=cursor
                )
                conversation_history.extend(result['messages'])
                if result['response_metadata'] is None:
                    cursor = ''
                else:
                    cursor = result['response_metadata']['next_cursor']
            df = pd.DataFrame(conversation_history)
            df = df[['text', 'user', 'ts']]
            df = df[df['text'].notnull()]
            df = df[df['user'].notnull()]
            df = df[df['text'].str.contains('|'.join(self.kw), case=False)]
            df['ts'] = pd.to_datetime(df['ts'].apply(self.ts), format='%Y-%m-%d %H:%M:%S')
            df['text'] = 1
            df.sort_values('ts',inplace=True)
            df.to_csv(os.getenv("SLACK_DATA_PATH"))
            self.db.afk_msg_store.delete_many({})
            self.db.afk_msg_store.insert_many(df.to_dict('records'))
        except SlackApiError as e:
            print(f"Got an error: {e.response['error']}")

    # Insert single message to db and local csv file
    def insert_single(self, msg):
        if any(word in msg['text'].lower() for word in self.kw):
            if msg['user'] is not None:
                msg['ts'] = self.ts(msg['ts'])
                self.in_data_prep(msg)

    def in_data_prep(self, msg=None):
        if msg == None:
            return self.mongodb_to_df()
        else:
            return self.input_data(msg)

    def input_data(self, msg):
        msg['text'] = 1
        self.db.afk_msg_store.insert_one(msg)
        if os.path.exists(os.getenv("SLACK_DATA_PATH")):
            df = self.file_clean_read()
        else:
            df = self.mongodb_to_df()
        df = df.append(msg, ignore_index=True)
        df.sort_values('ts',inplace=True)
        df.to_csv(os.getenv("SLACK_DATA_PATH"))

    def file_clean_read(self):
        df = pd.read_csv(os.getenv("SLACK_DATA_PATH"))
        df = df[['text', 'user', 'ts']]
        return df

    # Fetch data from 
    def mongodb_to_df(self):
        data = pd.DataFrame(list(self.db.afk_msg_store.find()))
        return data

    # Slack user_id to Slack name
    def userid_name(self, user_id, app):
        user_info = app.client.users_info(user=user_id)
        return user_info['user']['name']

    # Convert user_id to Slack real_name
    def userid_real_name(self, user_id, app):
        user_info = app.client.users_info(user=user_id)
        return user_info['user']['real_name']

    # Convert user_id to Slack display_name
    def userid_display_name(self, user_id, app):
        user_info = app.client.users_info(user=user_id)
        return user_info['user']['profile']['display_name']

    # Convert Slack name to user_id
    def name_userid(self, name, app):
        user_info = app.client.users_list()
        for user in user_info['members']:
            if user['name'] == name:
                return user['id']

    # Convert Slack real_name to user_id 
    def real_name_userid(self, real_name, app):
        user_info = app.client.users_list()
        for user in user_info['members']:
            if user['real_name'] == real_name:
                return user['id']

    # Validate time_range variable
    def time_range_validation(self, time_range):
        if len(time_range) == 2:
            freq = time_range[-1]
            periods = int(time_range[:-1])
            if freq in ['H', 'h'] and periods > 0 and periods <= 24:
                return {'res':True, 'msg':'Valid hour time range'}
            elif freq in ['D', 'd'] and periods > 0 and periods <= 365:
                return {'res':True, 'msg':'Valid day range'}
            else:
                return {'res':False, 'msg':'time must be in the form of "1H", "5h", "1D" or "10d" etc.'}
        else:
            return {'res':False, 'msg':'time_range must be only 2 characters long'}

    def command_info_extrator(self, command, msg, app):
        msg['text'] = msg['text'].replace(u'\xa0', u' ')
        name = msg['text'].split(' ')[0].replace('@', '')
        time_interval = 0
        if command == 'test':
            time_interval = msg['text'].split(' ')[1]
        uid = self.name_userid(name=name, app=app)
        return {'uid':uid, 'name':name, 'time_interval':time_interval}
