import requests
import time

for i in range(40):
    params = {
        'x': str(i),
        'y': '-16',
    }
    response = requests.get('http://localhost:8002/predict', params=params)
    if i == 30:
        time.sleep(30)
    time.sleep(2)