from itertools import count
from symbol import return_stmt
from typing import Optional
import requests
import constants
import json
from pycognito.aws_srp import AWSSRP
import os

USERNAME = ""
PASSWORD = ""

def get_AWS_tokens(username: str, password: str) -> Optional[str]:
    aws = AWSSRP(username=username, password=password, pool_id=constants.POOLID,
                 client_id=constants.CLIENTID, pool_region="eu-west-3")
    resp = aws.authenticate_user()
    if "AuthenticationResult" in resp and "IdToken" in resp["AuthenticationResult"]:
        return resp["AuthenticationResult"]["IdToken"]
    return None


def delete_audio(url: str, token: str) -> bool:
    headers = {
        "Accept": "application/vnd.api+json",
        "X-Platform": "ios",
        "X-Faba-Auth": constants.X_FABA_AUTH,
        "User-Agent": "MyFaba/42 CFNetwork/1404.0.5 Darwin/22.3.0",
        "Connection": "keep-alive",
        "Authorization": f"Bearer {token}",
    }
    response = requests.delete(url, headers=headers)

    if response.status_code == 204:
        return True
    else:
        print(f"Request failed with status code: {response.status_code}")
        return False


def upload_audio(contentid: int, file_path: str, token: str) -> bool:
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    url = "https://cms.myfaba.com/api/v2/profile/user-chapters"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
        "User-Agent": "MyFaba/43 CFNetwork/1404.0.5 Darwin/22.3.0"
    }
    chunk_size = 5 * 1024 * 1024
    with open(file_path, 'rb') as file:
        part_number = 1
        while chunk := file.read(chunk_size):
            files = {
                "userAudio": (file_name, chunk, "application/octet-stream")
            }
            data = {
                "part_number": part_number,
                "total_size": file_size,
                "characterContentId": contentid,
                "title": os.path.splitext(file_name)[0],
                "creator": "",
                "duration": 0.0
            }

            response = requests.post(url, files=files, data=data, headers=headers or {})
            if response.status_code != 201:
                print(f"Error uploading part {part_number}: {response.text}")
                return False

            part_number += 1

    print(f"Upload completed successfully.")
    return True
    

def getCharacterContents(onlyFabaMe, token) -> Optional[dict]:
    filter_contents = "true" if onlyFabaMe else "false"
    url = f"https://cms.myfaba.com/api/v2/profile/character-contents?include=userChapters&filter[fabaMe]={filter_contents}"

    headers = {
        "Accept": "application/vnd.api+json",
        "X-Platform": "ios",
        "X-Faba-Auth": constants.X_FABA_AUTH,
        "User-Agent": "MyFaba/42 CFNetwork/1404.0.5 Darwin/22.3.0",
        "Connection": "keep-alive",
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None

print("Retrieving aws token")
try:
    token = get_AWS_tokens(USERNAME,USERNAME)
except Exception as e:
    print(f"Error getting AWS token: {e}")
    exit(1)

if token is not None:
    print("Retrieving fabaMe character contents")
    items = getCharacterContents(True, token)["data"]
    for item in items:
        attributes = item['attributes']
        meta = item['meta']
        print("-------------------------------------")
        print(f"Id: {item['id']}")
        print(f"Title: {attributes['title']}")
        print(f"Tracks Count: {meta['tracksCount']}")
        print(f"Duration: {meta['duration']}")
        print(f"Remaining Time: {meta['remainingTime']}")
        print(f"Time Limit: {meta['timeLimit']}")
        content_id = input("Please enter content id: ")
        print(f"You entered: {content_id}")
        selection = input("0 => Upload audio folder\n1 => List audio files\n2 => Delete all files\nPlease enter selection: ")
        if selection == "0":
            folder_path = input("Please enter audio folder path: ")
            folder_path = os.path.normpath(folder_path)
            print(f"You entered: {folder_path}")
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            for file in files:
                print("Uploading file: " + file)
                file_path = os.path.join(folder_path, file)
                if not upload_audio(int(content_id), file_path, token):
                    break
            print("All done! bye")
        elif selection == "1":
            userChapters = item['relationships']['userChapters']['data']
            for chapter in userChapters:
                print("-------------------------------------")
                print(f"Id: {chapter['id']}")
                print(f"Chapter: {chapter['attributes']['title']}")
                print(f"Duration: {chapter['attributes']['duration']}")
        elif selection == "2":
            userChapters = item['relationships']['userChapters']['data']
            for chapter in userChapters:
                self_link = chapter['links']['self']
                title = chapter['attributes']['title']
                print("Deleting file: " + title)
                if not delete_audio(self_link, token):
                    break
            print("All done! bye")
else:
    print("Login failed!")



