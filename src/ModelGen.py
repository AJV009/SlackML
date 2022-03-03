from math import sqrt
import itertools
import json, os, pandas as pd, numpy as np
from datetime import datetime
from prophet import Prophet
from prophet.diagnostics import cross_validation
from prophet.diagnostics import performance_metrics
from prophet.serialize import model_to_json, model_from_json
from src.HelperFunc import HelperFunc
from sklearn.metrics import mean_squared_error
from dotenv import load_dotenv

"""
TODO: 
1. Complete the modelAccTest with cross-validation testing metod from prophet diagnostics.
2. Implement HyperParameter tuning in modelTrain.
3. Each user gets it own model, models are named with datetime for easy tracking.
4. Use AutoPred for auto rebuilding of models.
"""

class ModelGen:

    def __init__(self) -> None:
        load_dotenv()
        self.helper = HelperFunc()
        self.model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True)
        self.model_params = {}

    # TODO: Complete modelAccTest
    def modelTrain(self, data_source="local", userid=None, time_col='ts', time_gap='1H', test=False):
        data = pd.DataFrame()
        if data_source == "local":
            try:
                data = self.helper.file_clean_read()
            except:
                data_source = "cloud"
        if data_source == "cloud":
            data = self.helper.in_data_prep()
        if data.empty:
            return {'msg': 'No data found to train/test, please run /refresh_db to fetch data from Slack.'}
        else:
            if test:
                res = self.modelAccTest(data, userid)
            return res
            # if self.modelLocal(userid)['status'] == False:
            #     pass
            # else:
            #     pass
            return {'msg': 'Model failed.'}

    def modelAccTest(self, data, userid=None):
        data = self.helper.model_data_prep(data, userid=userid)
        self.model.fit(data)
        df_cv = cross_validation(self.model, horizon = 1)
        df_p = performance_metrics(df_cv)
        # accuracy score from 1 to 10 
        score = 10
        # df_cv = cross_validation(testModel, initial='730 days', period='180 days', horizon = '365 days')
        return {'msg': 'Model trained successfully.', 'score': score}

    def modelPredict(self, freq, periods):
        future_data = pd.DataFrame(periods=periods, freq=freq, include_history=False)
        forecast = self.model.predict(future_data)
        return forecast

    def modelSave(self, userid=None):
        model_name = 'pm_' + userid + '_' + str(datetime.now()) + '.json'
        with open(model_name, 'w') as fout:
            json.dump(model_to_json(self.model), fout)  # Save model

    def modelLocal(self, userid=None, day_gap=4):
        model_name_start = 'pm_' + userid + '_'
        model_files = [f for f in os.listdir('models/') if f.startswith(model_name_start)]
        if len(model_files) > 0:
            model_file = model_files[0]
            model_datetime = model_file.split('_')[-1].split('.')[0]
            model_datetime = datetime.strptime(model_datetime, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - model_datetime).days > day_gap:
                for f in model_files:
                    os.remove(f)                    
            else:
                with open(model_file, 'r') as fin:
                    self.model = Prophet()
                    self.model = model_from_json(json.load(fin))
                return {'status':True, 'msg': 'Model loaded successfully.'}
        return {'status':False, 'msg': 'No model found to load.'}
