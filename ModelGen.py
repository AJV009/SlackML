from numpy import empty
from prophet import Prophet
from prophet.diagnostics import cross_validation
from HelperFunc import HelperFunc
from sklearn.model_selection import train_test_split
import pandas as pd
from sklearn.metrics import mean_squared_error
from math import sqrt

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

    def modelTrain(self, data_source="local", userid=None, time_gap='1H'):
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
            data = self.helper.model_data_prep(data, userid=userid, time_gap=time_gap)
            self.model.fit(data)
            return {'msg': 'Model trained successfully.'}

    def modelAccTest(self, data):
        testModel = Prophet()
        testModel.fit(data)
        # print('Size of data: ', len(data))
        # df_cv = cross_validation(testModel, initial='730 days', period='180 days', horizon = '365 days')

    def modelPredict(self, freq, periods):
        future_data = pd.DataFrame(periods=periods, freq=freq, include_history=False)
        forecast = self.model.predict(future_data)
        return forecast
