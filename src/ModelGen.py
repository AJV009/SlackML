import json, os, pandas as pd
from datetime import datetime
from prophet import Prophet
from prophet.diagnostics import cross_validation
from prophet.diagnostics import performance_metrics
from prophet.serialize import model_to_json, model_from_json
from src.HelperFunc import HelperFunc
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

    # main function to train model
    def modelTrain(self, time_pred_range, userid=None, time_col='ts', time_gap='1H', ):
        data = pd.DataFrame()
        # check data source and load data
        data = self.helper.init_data_prep(data_source="local")
        # check if data is empty
        if data.empty:
            return {'msg': 'No data found to train/test, please run /refresh_db to fetch data from Slack.' ,'status':False}
        else:
            # Check if model already exists for the user and load it if exists else train new model and save it for future use.
            model_data = self.modelTest(data, userid=userid)
            
            return {'msg': 'Model failed.', 'status':False} 
    
    # predict user leave
    def modelTest(self, data, time_pred_range, userid=None):
        model_locally_saved = self.loadLocalModel(userid=userid)['status']
        score = 0
        if not model_locally_saved:
            # Filter and prep data for new model.
            data = self.helper.model_data_prep(data, userid=userid)
            # load model from local file
            self.model.fit(data)
            if len(data) < 14:
                return {'msg': 'Not enough data to train/test model.','status':False}
        df_cv = cross_validation(self.model, horizon = "168 hours")
        df_cv_metrics = performance_metrics(df_cv)
        score = df_cv_metrics.loc['MSE', 'train']
        print(score)
        # TODO
        if score < 0.1:
            self.modelSave(userid=userid)
            return {'msg': 'Model trained successfully.', 'status':True}
        else:
            return {'msg': 'Model failed.', 'status':False}

    # load model from local file if exists also check if model is too old.
    def loadLocalModel(self, userid=None, day_gap=4):
        # model name pattern
        model_name_start = 'pm_' + userid + '_'
        # list of all models
        model_files = [f for f in os.listdir('models/') if f.startswith(model_name_start)]
        if len(model_files) > 0:
            # get the first model from the list
            model_file = model_files[0]
            # get the last modified date of the model
            model_datetime = model_file.split('_')[-1].split('.')[0]
            model_datetime = datetime.strptime(model_datetime, '%Y-%m-%d %H:%M:%S')
            # delete model if older than the day_gap
            if (datetime.now() - model_datetime).days > day_gap:
                for f in model_files:
                    os.remove(f)
                    return {'msg': 'Model is older than ' + str(day_gap) + ' days.' ,'status':False}
            else:
                # load model from local file
                with open(model_file, 'r') as fin:
                    self.model = Prophet()
                    self.model = model_from_json(json.load(fin))
                return {'msg': 'Model loaded successfully.', 'status':True}
        return {'msg': 'No model found to load.', 'status':False}

    def modelSave(self, userid=None):
        model_name = 'pm_' + userid + '_' + str(datetime.now()) + '.json'
        with open(model_name, 'w') as fout:
            json.dump(model_to_json(self.model), fout)  # Save model

