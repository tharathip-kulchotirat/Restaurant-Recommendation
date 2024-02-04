import mlflow
import os
from dotenv import load_dotenv
load_dotenv()
from sklearn.neighbors import NearestNeighbors
import pickle

def register_model():
    # Load sklearn model
    mlflow.set_tracking_uri(os.getenv("MLFLOW_URI"))
    with open("ml_model/model.pkl", "rb") as f:
        model: NearestNeighbors = pickle.load(f)

    with mlflow.start_run():
        mlflow.sklearn.log_model(model, "recommend", registered_model_name="recommend")

    runs = mlflow.search_runs(experiment_ids=[0])
    
    # Register Model
    mlflow.register_model(f"runs:/{runs.iloc[0, :]['run_id']}/recommend", "recommend")
    model = mlflow.sklearn.load_model("runs:/" + runs.iloc[0, :]['run_id'] + "/recommend")


if __name__ == "__main__":
    register_model()
