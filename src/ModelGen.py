from sklearn.metrics import mean_squared_error
from math import sqrt
import json, os, pandas as pd, numpy as np
from datetime import datetime
from prophet import Prophet
from prophet.diagnostics import cross_validation
from prophet.serialize import model_to_json, model_from_json
from HelperFunc import HelperFunc
from sklearn.model_selection import train_test_split

"""
TODO: 
1. Complete the modelAccTest with cross-validation testing metod from prophet diagnostics.
2. Implement HyperParameter tuning in modelTrain.
3. Each user gets it own model, models are named with datetime for easy tracking.
4. Use AutoPred for auto rebuilding of models.
"""

class ModelGen:
    def __init__(self) -> None:
        self.helper = HelperFunc()
        self.model = Prophet()
        self.model_params = {}

    # TODO: Complete modelAccTest
    def modelTrain(self, data_source="local", userid=None, time_col='ts', time_gap='1H'):
        # create empty dataframe
        data = pd.DataFrame()
        # Read the data from local CSV file
        if data_source == "local":
            # try to read the data from local CSV file
            try:
                data = pd.read_csv('conversation_history.csv')
            except:
                data = self.helper.mongodb_to_df()
        elif data_source == "cloud":
            # read complete collection from mongo db to pandas dataframe
            data = self.helper.mongodb_to_df()
        # check if data dataframe is empty
        if data.empty:
            return {'msg': 'No data found to train, please run /refresh_db to fetch data from Slack.'}
        else:
            # if modelLocal returns False, then train the model
            if self.modelLocal(userid)['status'] == False:
                pass
            else:
                pass
            return {'msg': 'Model trained successfully.'}

    # TODO: Complete modelAccTest
    def modelAccTest(self, data):
        testModel = Prophet()
        testModel.fit(data)
        # df_cv = cross_validation(testModel, initial='730 days', period='180 days', horizon = '365 days')

    def modelPredict(self, freq, periods):
        future_data = pd.DataFrame(periods=periods, freq=freq, include_history=False)
        forecast = self.model.predict(future_data)
        return forecast

    def modelSave(self, userid=None):
        # Save this Prophet model to disk
        model_name = 'pm_' + userid + '_' + str(datetime.now()) + '.json'
        with open(model_name, 'w') as fout:
            json.dump(model_to_json(self.model), fout)  # Save model

    def modelLocal(self, userid=None, day_gap=4):
        model_name_start = 'pm_' + userid + '_'
        model_files = [f for f in os.listdir('models/') if f.startswith(model_name_start)]
        print(model_files)
        if len(model_files) > 0:
            model_file = model_files[0]
            # split the filename to get the datetime
            model_datetime = model_file.split('_')[-1].split('.')[0]
            # convert datetime to datetime object
            model_datetime = datetime.strptime(model_datetime, '%Y-%m-%d %H:%M:%S')
            # check if the model is older than 1 week
            if (datetime.now() - model_datetime).days > day_gap:
                for f in model_files:
                        os.remove(f)                    
            else:
                with open(model_file, 'r') as fin:
                    self.model = Prophet()
                    self.model = model_from_json(json.load(fin))
                return {'status':True, 'msg': 'Model loaded successfully.'}
        return {'status':False, 'msg': 'No model found to load.'}
