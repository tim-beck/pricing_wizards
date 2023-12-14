import os
import numpy as np
import time
import math
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.base import BaseEstimator
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance
from sklearn.model_selection import RandomizedSearchCV, GridSearchCV, cross_val_score
from sklearn.metrics import mean_squared_error, explained_variance_score, mean_absolute_error, r2_score, mean_squared_log_error, median_absolute_error
from sklearn.utils import Bunch
from typing import Type
from tabulate import tabulate

from utils.object import MLModelConfig

def two_step_hyperparameter_tuning(model_class: Type[BaseEstimator], model_config: MLModelConfig, param_grid: dict) -> Type[Bunch]:
    """
    Perform two-step hyperparameter tuning using Random Search followed by Grid Search.

    Parameters:
    - model_class (BaseEstimator): The machine learning model class (e.g., SVR).
    - model_config (MLModelConfig): An object containing training and test data (X_train, y_train, X_test, y_test).
    - param_grid (dict): The hyperparameter grid to search.

    Returns:
    Bunch: A Bunch containing the results of the hyperparameter tuning
    """

    X = model_config.X
    X_train = model_config.X_train
    y_train = model_config.y_train
    X_test = model_config.X_test
    y_test = model_config.y_test

    # Define categorical features
    categorical_features = X.columns.tolist()

    # Create a column transformer for one-hot encoding
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough'
    )

    # Create a pipeline with named steps
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', model_class)
    ])

    random_search = RandomizedSearchCV(
        pipeline,
        param_distributions=param_grid,
        n_iter=10,
        scoring='neg_mean_squared_error',
        cv=5,
        random_state=42
    )

    # Use Random Search as first step of the hyperparameter tuning
    random_search.fit(X_train, y_train)

    # Get the best hyperparameters from Random Search
    best_params_random: list = random_search.best_params_

    # Use the best hyperparameters from Random Search as initial values for Grid Search
    grid_search_params = {
        key: [value] for key, value in best_params_random.items()
    }

    grid_search = GridSearchCV(
        pipeline,
        grid_search_params,
        scoring='neg_mean_squared_error',
        cv=5
    )
    grid_search.fit(X_train, y_train)

    # Get the best hyperparameters from Grid Search
    best_params_grid: list = grid_search.best_params_

    # Train the final model with the best hyperparameters from Grid Search
    final_model = grid_search.best_estimator_

    # Evaluate the model using cross-validation and calculates the mean
    cv_scores: list = cross_val_score(final_model, X_train, y_train, scoring='neg_mean_squared_error', cv=5)
    mse_mean_cv: float = np.mean(cv_scores)

    # Train the final model on the entire training set, measuring the training time in seconds
    start_time = time.time()
    final_model.fit(X_train, y_train)
    end_time = time.time()

    # Calculate training time
    training_time = end_time - start_time

    # Evaluate the final model on the test set
    y_pred_test = final_model.predict(X_test)
    mse_test: float = mean_squared_error(y_test, y_pred_test)

    # Calculate permutation importances for the regressor
    feature_importances = permutation_importance(final_model, X_test, y_test, n_repeats=10, random_state=42).importances_mean

    output: type[Bunch] = Bunch(
        params = best_params_grid,
        model = final_model,
        feature_importances = list(zip(X.columns, feature_importances)),
        training_time = training_time,
        mse_mean_cv = mse_mean_cv,
        mse_test = mse_test,
        y_pred = y_pred_test
    )

    return output

def print_prediction_summary(label: str, y_true: pd.Series, y_pred: pd.Series) -> None:
    """
    Print a summary of regression evaluation metrics.

    Parameters:
    - y_true (list): True values of the target variable.
    - y_pred (list): Predicted values of the target variable.

    Returns:
    None
    """

    evs = round(explained_variance_score(y_true, y_pred), 4)
    msle = round(mean_squared_log_error(y_true, y_pred), 4)
    r2 = round(r2_score(y_true, y_pred), 4)
    mae = round(mean_absolute_error(y_true, y_pred), 4)
    mse = round(mean_squared_error(y_true, y_pred), 4)
    medae = round(median_absolute_error(y_true, y_pred), 4)
    rmse = round(np.sqrt(mse), 4)

    table = [
        ["Explained Variance", evs],
        ["Mean Squared Log Error", msle],
        ["R2", r2],
        ["MAE", mae],
        ["MSE", mse],
        ["Median Absolute Error", medae],
        ["Root Mean Squared Error", rmse]
    ]

    print(tabulate(table, headers=[f"Metric ({label})", "Value"], tablefmt="pretty", numalign="right", stralign="right", colalign=("left", "right")))

def plot_actual_predicted(results: Type[Bunch], y_test: pd.Series) -> None:
    """
    Generate scatter plots for actual vs. predicted values for each model in the results.

    Parameters:
    - results (Type[Bunch]): A nested dictionary containing model results. Each model should have a 'y_pred' attribute
                            representing predicted values and a 'label' attribute for identification.
    - y_test (pd.Series): The actual values for the test set.

    Returns:
    None
    """

    models = [model for models in results.values() for model in models]

    num_models = len(models)
    num_cols = 2
    num_rows = math.ceil(num_models / num_cols)

    fig, axs = plt.subplots(num_rows, num_cols, figsize=(18, 6*num_rows), tight_layout=True)
    axs = axs.flatten()

    for i, model in enumerate(models):
        # Create scatter plots for test set
        axs[i].scatter(y_test, model.y_pred, alpha=0.25)
        axs[i].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'k', lw=1)
        axs[i].set_title(model.label)
        axs[i].set_xlabel('Actual Values')
        axs[i].set_ylabel('Predicted Values')

    plt.suptitle("Actual vs. Predicted values by model")

    # Save the plot
    if not os.path.exists("visualization"):
        os.makedirs("visualization")

    fig.savefig("visualization/plot_actual_predicted")

def plot_residuals(results: Type[Bunch], y_test: pd.Series):
    """
    Generate scatter plots of residuals for each model in the results.

    Parameters:
    - results (Type[Bunch]): A nested dictionary containing model results. Each model should have a 'y_pred' attribute
                            representing predicted values and a 'label' attribute for identification.
    - y_test (pd.Series): The actual values for the test set.

    Returns:
    None
    """

    models = [model for models in results.values() for model in models]

    num_models = len(models)
    num_cols = 2
    num_rows = math.ceil(num_models / num_cols)

    fig, axs = plt.subplots(num_rows, num_cols, figsize=(18, 6*num_rows), tight_layout=True)

    for i, model in enumerate(models):
        # Calculate residuals
        prediction_error = y_test.iloc[i] - model.y_pred

        # Extract the subplot for the current model
        row = i // num_cols
        col = i % num_cols

        # Plot the scatter plot on the specific subplot
        axs[row, col].scatter(model.y_pred, prediction_error, alpha=0.5)
        plt.axhline(y=0, color='r', linestyle='--')
        axs[row, col].set_title(model.label)
        axs[row, col].set_xlabel('Predicted Values')
        axs[row, col].set_ylabel('Prediction Errors')

    plt.suptitle("Residual values by model")

    # Save the plot
    if not os.path.exists("visualization"):
        os.makedirs("visualization")

    fig.savefig("visualization/plot_residuals")

def plot_feature_importances(ranked_feature_importances: pd.DataFrame) -> None:
    """
    Plot bar charts for average feature importances.

    Parameters:
    - ranked_feature_importances (pd.DataFrame): DataFrame with ranked feature importances.

    Returns:
    None
    """
    fig, ax = plt.subplots(tight_layout=True)

    # Bar plot for average feature importances
    sns.barplot(x=ranked_feature_importances.index, y=ranked_feature_importances['average'], hue=ranked_feature_importances.index, legend=False)
    plt.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax.set_title('Average Feature Importances')
    ax.set_xlabel('Average Importance')
    ax.set_ylabel('Features')

    # Save the plot
    if not os.path.exists("visualization"):
        os.makedirs("visualization")

    fig.savefig("visualization/plot_feature_importances")