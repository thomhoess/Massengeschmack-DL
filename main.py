import os
import time
import requests
from datetime import datetime
import requests_cache
from mutagen.mp4 import MP4


# Enable caching of API requests/responses for 24h
requests_cache.install_cache(cache_name='mgtv_cache', backend='sqlite', expire_after=86400)


def api_call(params, username, password):
    # The API has a rate limiter, this while loop will retry if the API spits out an error because of an exceeded rate limit
    while True:
        response = requests.get('https://' + username + ':' + password + '@massengeschmack.tv/api/v1/', params=params)
        response = response.json()

        # Check if retryAfter is set in response of API (attr only exists if rate limited)
        try:
            response["retryAfter"]
        except KeyError:
            response["retryAfter"] = None

        # If rate limit reached, wait the needed time and start the loop over again
        if response["retryAfter"] is not None:
            retry = response["retryAfter"]
            time.sleep(retry)
            continue
        else:
            break

    return response


def list_formats():
    # List all formats and their ids
    formats = open("formats.txt", "r", encoding="utf-8")
    formats = formats.read()

    return formats


def create_list(pid):
    # Create empty array to store ids of videos to be downloaded
    downloadIds = []

    # Get list of all episodes of specified format via API
    params = (
        ("action", "getFeed"),
        ('from', "[" + str(pid) + "]"),
        ('page', "1")
    )

    # Store number of pages (API does pagination)
    pages = api_call(params, username, password)["pages"]

    # Cycle through all pages of the specified format and append the video identifier in the array
    for i in range(0, pages):
        params = (
            ("action", "getFeed"),
            ('from', "[" + str(pid) + "]"),
            ('page', i)
        )
        page = api_call(params, username, password)
        for v in page["eps"]:
            downloadIds.append(v["identifier"])

    return downloadIds


def dl_video(id, path):
    # Get clip information from API
    params = (
        ('action', "getClip"),
        ('identifier', id),
    )
    response = api_call(params, username, password)

    # Format various information
    fileType = "." + response["files"][0]["url"].split(".")[-1]
    fileName = response["title"] + " - " + datetime.utcfromtimestamp(response["date"]).strftime('%Y-%m-%d')

    # Download the video via system-wide install of yt-dlp
    ytdlpCmd = 'yt-dlp https:' + response["files"][0]["url"] + ' -o "' + fileName + fileType + '" -P "' + path
    os.system(ytdlpCmd)

    # Modify metadata after download
    video = MP4(path + fileName + fileType)
    video["desc"] = response["desc"]
    video["date"] = datetime.utcfromtimestamp(response["date"]).strftime('%Y-%m-%d')
    video.save()

# Get username and password to have access to download videos
username = input("E-Mail Adresse: ")
username = username.replace("@", "--at--")

password = input("Passwort: ")

# Ask for download destination and add trailing slash
path = input("Download-Pfad: ")
path = os.path.join(path, '')

# List all available formats and their pid
print("Formate und deren ID:")
print(list_formats())

# Ask for program id
pid = input("ID des Formats: ")

# Create list of series
list = create_list(pid)

# Cycle through episodes and download videos
for i in list:
    dl_video(i, path)
