import requests

jobID = 1234
url = f'http://127.0.0.1:5000/{jobID}/upload_file'
fpaths = ['file.txt']


for fpath in fpaths:
    response = requests.post(
        url=url,
        files={"file": [fpath, open(fpath, 'rb'), 'application/json']},
    )

    print(response.json())
