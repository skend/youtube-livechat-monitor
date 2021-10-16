import os
import json
import time
import pymongo

import googleapiclient.discovery

# no fault tolerance lolololol
# magic numbers ftw!!! poggers

def get_api_key():
    with open("client_secrets.json") as f:
        data = json.load(f)
        return data['API_KEY']
    return None


def get_collection():
    conn_str = "mongodb://localhost:27017"
    client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)

    try:
        client.server_info()
        print("Successfully connected to local mongo instance")
    except Exception:
        print("Unable to connect to the server.")

    db = client["db"]
    return db["messages"]


def main():
    collection = get_collection()
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = get_api_key()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    channel_id = get_youtube_channel_id(youtube)
    livestream_id = get_livestream_id(youtube, channel_id)

    if livestream_id != None:
        chat_id = get_chat_id(youtube, livestream_id)
        monitor_chat(youtube, chat_id, collection)


def monitor_chat(youtube, chat_id, collection, page_token=None):
    request = youtube.liveChatMessages().list(
        liveChatId=chat_id,
        part="snippet",
        pageToken=page_token
    )
    response = request.execute()
    next_page_token = response['nextPageToken']

    write_messages_to_db(response['items'])

    time.sleep(10)
    monitor_chat(youtube, chat_id, collection, page_token=next_page_token)


def write_messages_to_db(items, collection):
    messages = []
    for item in items:
        messages.append(
            {   
                'timestamp': item['snippet']['publishedAt'], 
                'channel': item['snippet']['authorChannelId'], 
                'content': item['snippet']['displayMessage']
            }
        )

    if len(messages) > 0:
        obj = collection.insert_many(messages)
        print('Inserted the following:')
        print(obj.inserted_ids)



def get_chat_id(youtube, livestream_id):
    request = youtube.videos().list(
        part="liveStreamingDetails",
        id=livestream_id
    )
    response = request.execute()

    return response['items'][0]['liveStreamingDetails']['activeLiveChatId']



def get_youtube_channel_id(youtube):
    request = youtube.channels().list(
        part="id",
        forUsername="destiny"
    )
    response = request.execute()

    return response['items'][0]['id']


def get_livestream_id(youtube, channel_id):
    is_live, livestream_id = channel_is_live(youtube, channel_id)
    if is_live:
        return livestream_id

    return None


def channel_is_live(youtube, channel_id):
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        channelType="any",
        eventType="live",
        type="video"
    )
    response = request.execute()

    return response['pageInfo']['totalResults'] > 0, \
           response['items'][0]['id']['videoId']


if __name__ == "__main__":
    main()