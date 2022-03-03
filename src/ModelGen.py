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
1. Remove Analyze command and use one single predict command to predict user leave.
2. Add crossvalidation and hyperparameter tuning to the main model.
3. Implement HyperParameter tuning in modelTrain.
4. Each user gets it own model, models are named with datetime for easy tracking.
5. Use AutoPred for auto rebuilding of models.
6. Use parrallism for modelTrain and avoid using more than 30mins per user for complete process

ref: 
- https://medium.com/dropout-analytics/cross-validating-prophet-at-scale-72b1a21b6433
- https://towardsdatascience.com/implementing-facebook-prophet-efficiently-c241305405a3
- https://github.com/Ritvik29/Walmart-Demand-Prediction 
"""

class ModelGen:

    def __init__(self) -> None:
        load_dotenv()
        self.helper = HelperFunc()
        self.model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True)
        self.model_params = {}

    # TODO: Complete modelAccTest
    def modelTrain(self, data_source="local", userid=None, time_col='ts', time_gap='1H'):
        data = pd.DataFrame()
        if data_source == "local":
            try:
                data = self.helper.file_clean_read()
            except:
                data_source = "cloud"
        if data_source == "cloud":
            data = self.helper.in_data_prep()
        if data.empty:
            return {'msg': 'No data found to train/test, please run /refresh_db to fetch data from Slack.' ,'status':False}
        else:
            # if self.modelLocal(userid)['status'] == False:
            #     pass
            # else:
            #     pass
            return {'msg': 'Model failed.', 'status':False} 

    # def modelAccTest(self, data, userid=None):
    #     score = 0
    #     data = self.helper.model_data_prep(data, userid=userid)
    #     if len(data) < 14:
    #         return {'msg': 'Not enough data to train/test model.','status':False}
    #     self.model.fit(data)
    #     df_cv = cross_validation(self.model, horizon = 7)
    #     df_p = performance_metrics(df_cv)
    #     return {'msg': 'Model trained successfully.', 'score': score, 'status':True}

    # def modelPredict(self, freq, periods):
    #     future_data = pd.DataFrame(periods=periods, freq=freq, include_history=False)
    #     forecast = self.model.predict(future_data)
    #     return forecast

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

    def modelSave(self, userid=None):
        model_name = 'pm_' + userid + '_' + str(datetime.now()) + '.json'
        with open(model_name, 'w') as fout:
            json.dump(model_to_json(self.model), fout)  # Save model

