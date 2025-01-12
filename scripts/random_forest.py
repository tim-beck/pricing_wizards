# Data Manipulation
from typing import Type

# Scikit learn
from sklearn.ensemble import RandomForestRegressor
from sklearn.utils import Bunch

# Load helpers and custom dataset class
from utils.helpers import two_step_hyperparameter_tuning, print_prediction_summary, save_model

def run_rf(prediction_instance: Type["Prediction"]) -> Type[Bunch]:
    """
    Run a machine learning model using hyperparameter tuning with both GridSearchCV and RandomizedSearchCV.

    Parameters:
    - prediction_instance (Prediction): An object containing data and configurations for model training and testing.

    Returns:
    - results (Type[Bund]): A dictionary containing the results of hyperparameter tuning using GridSearchCV and RandomizedSearchCV.
    """

    # Defines a set of values to explore during the hyperparameter tuning process
    param_dist: dict = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }

    # Create a Random Forest model
    rf = RandomForestRegressor()

    # Using param_dist for two step hyperparameter tuning with Random Forest
    output_rf: Type[Bunch] = two_step_hyperparameter_tuning(rf, prediction_instance, param_dist)

    # Add label to output
    output_rf.label = 'Random Forest'

    # Saving model
    path = f'models/pickled_models/prediction_{"_".join(output_rf.label.lower().split())}.pkl'
    save_model(output_rf, path)

    output: Type[Bunch] = Bunch(
        standard = output_rf
    )

    # Printing a summary of the results
    print_prediction_summary('Random Forest', prediction_instance.y_test, output_rf.y_pred)

    return output