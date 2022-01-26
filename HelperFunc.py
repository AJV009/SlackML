import os
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
        # convert timestamp to datetime function
        self.ts = lambda x: datetime.datetime.fromtimestamp(float(x)).strftime('%Y-%m-%d %H:%M:%S')
        load_dotenv()
        # mongo client
        client = MongoClient(os.getenv("MONGO_URI"))
        self.db = client.afk_db


    # Bin the time series
    def time_bin_binaryfy(self, df, time_col,time_gap):
        temp_df = df.copy()
        # set the time column as index
        temp_df.set_index(temp_df[time_col], inplace=True)
        # resample and sum based on the time_gap, example 1H
        temp_df = temp_df.resample(time_gap).sum()
        return temp_df

    def user_filter(self, df, user=None):
        temp_df = df.copy()
        # if user is not None, filter the dataframe
        if user is not None:
            temp_df = temp_df[temp_df['user']==user]
        # drop the user column
        temp_df.drop(['user'], axis=1, inplace=True)
        return temp_df

    def model_data_prep(self, df, userid=None, time_col='ts', time_gap='1h'):
        prep_data = df.copy()
        # filter the dataframe with user_id
        prep_data = self.user_filter(df=prep_data, user=userid)
        # bin the time series for a persistent time series model
        prep_data = self.time_bin_binaryfy(df=prep_data, time_col=time_col, time_gap=time_gap)
        # convert index to ds column
        prep_data['ds'] = prep_data.index
        # convert text/data column to y column
        prep_data['y'] = prep_data['text']
        # drop the text column
        prep_data.drop(['text'], axis=1, inplace=True)
        # drop the index
        prep_data.reset_index(drop=True, inplace=True)
        return prep_data

    # Refresh complete conversation history with DB and local CSV file
    def refresh_db(self, app, channel_id, db):
        conversation_history = []
        # Fetch data and save.
        try:
            # Set the cursor to 0
            cursor = '0'
            # Until the cursor is not equal to '' continue fetching data
            while (cursor != ''):
                # Fetch data from Slack
                result = app.client.conversations_history(
                    channel=channel_id,
                    limit=70,
                    cursor=cursor
                )
                # Append the data to conversation_history
                conversation_history.extend(result['messages'])
                # Set the cursor to the next page if it exists or set cursor to ''
                if result['response_metadata'] is None:
                    cursor = ''
                else:
                    cursor = result['response_metadata']['next_cursor']
            # save conversation history to a dataframe
            df = pd.DataFrame(conversation_history)
            df = df[['text', 'user', 'ts']]
            # drop rows with empty text and user
            df = df[df['text'].notnull()]
            df = df[df['user'].notnull()]
            # check if the message has any of the keywords
            df = df[df['text'].str.contains('|'.join(self.kw), case=False)]
            # convert linux timestamp to datetime
            df['ts'] = pd.to_datetime(df['ts'].apply(self.ts), format='%Y-%m-%d %H:%M:%S')
            # categorize the messages
            df['text'] = 1
            df.sort_values('ts',inplace=True)
            # Save to csv
            df.to_csv('conversation_history.csv')
            # clear data from 'afk_msg_store' collection
            self.db.afk_msg_store.delete_many({})
            # insert data to 'afk_msg_store' collection
            self.db.afk_msg_store.insert_many(df.to_dict('records'))
        except SlackApiError as e:
            print(f"Got an error: {e.response['error']}")

    # Insert single message to db and local csv file
    def insert_single(self, msg, db):
        if any(word in msg['text'].lower() for word in self.kw):
            # check if user is not null
            if msg['user'] is not None:
                # convert timestamp to datetime
                msg['ts'] = self.ts(msg['ts'])
                # insert to mongodb db
                self.db.afk_msg_store.insert_one(msg)
                # Update the local CSV file
                # read conversation_history.csv
                df = pd.read_csv('conversation_history.csv')
                # append msg to conversation_history.csv
                df = df.append(msg, ignore_index=True)
                # sort by timestamp
                df.sort_values('ts',inplace=True)
                # save to csv
                df.to_csv('conversation_history.csv')
    
    def mongodb_to_df(self):
        # fetch complete collection from self.db.afk_msg_store and convert to dataframe and return
        return pd.DataFrame(list(self.db.afk_msg_store.find()))

    # Slack user_id to Slack name
    def userid_name(self, user_id, app):
        # Get user with user == user_id
        user_info = app.client.users_info(user=user_id)
        # return the user name
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
        # get all users
        user_info = app.client.users_list()
        # loop through all users
        for user in user_info['members']:
            # check if the user name matches
            if user['name'] == name:
                # return the user id
                return user['id']
    
    # Convert Slack real_name to user_id 
    def real_name_userid(self, real_name, app):
        user_info = app.client.users_list()
        for user in user_info['members']:
            if user['real_name'] == real_name:
                return user['id']

    # Validate time_range variable
    def time_range_validation(self, time_range):
        # Check if len of time_range is 2
        if len(time_range) == 2:
            # extract frequency and period from time_range
            freq = time_range[-1]
            periods = int(time_range[:-1])
            # Check if frequency is Hour or Day because others will be inconsistent
            if freq in ['H', 'h'] and periods > 0 and periods <= 24:
                return {'res':True, 'msg':'Valid hour time range'}
            elif freq in ['D', 'd'] and periods > 0 and periods <= 365:
                return {'res':True, 'msg':'Valid day range'}
            else:
                return {'res':False, 'msg':'time must be in the form of "1H", "5h", "1D" or "10d" etc.'}
        else:
            return {'res':False, 'msg':'time_range must be only 2 characters long'}
