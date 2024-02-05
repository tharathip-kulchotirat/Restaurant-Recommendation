import pandas as pd
import numpy as np
from locust import HttpUser, task, between
from pathlib import Path

request_file = Path(__file__).parent / "request.parquet"

class RecommendationUser(HttpUser):
    wait_time = between(1, 2)  # Time between requests in seconds
    
    def load_request_params(self):
        # Load parameters from request.parquet file
        df = pd.read_parquet(request_file)
        return df.to_dict(orient="records")

    @task
    def recommend_request(self):
        # Load request parameters from the file
        params_list = self.load_request_params()

        for params in params_list:
            # Convert params to URL query string
            query_string = "&".join([f"{key}={value}" for key, value in params.items() if isinstance(value, (int, float)) and not np.isnan(value)])

            # Construct the URL with the query string
            url = f"/recommend/{params['user_id']}?{query_string}"

            # Send the request
            response = self.client.get(url)
            
            # Check if the response is successful
            if response.status_code == 200:
                # Print or handle the response data as needed
                print(response.json())
            else:
                # Handle unsuccessful response, e.g., log the error
                print(f"Request failed with status code: {response.status_code}")