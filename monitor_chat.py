import os
import json
import time
import pymongo
import constants

import googleapiclient.discovery

# no fault tolerance lolololol
# magic numbers ftw!!! poggers

def get_api_key():
    with open("client_secrets.json") as f:
        data = json.load(f)
        return data['API_KEY']
    return None


def get_db():
    client = pymongo.MongoClient(constants.MONGO_CONNECTION_STRING, serverSelectionTimeoutMS=5000)

    try:
        client.server_info()
        print("Successfully connected to local mongo instance")
    except Exception:
        print("Unable to connect to the server.")

    return client["db"]


def main():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = get_api_key()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    channel_id = constants.CHANNEL_ID if constants.CHANNEL_ID != None else get_youtube_channel_id(youtube)
    livestream_id = get_livestream_id(youtube, channel_id)

    if livestream_id != None:
        chat_id = get_chat_id(youtube, livestream_id)
        db = get_db()
        monitor_chat(youtube, chat_id, db[constants.CHANNEL_NAME], db[constants.CHANNEL_NAME + "_users"])


def monitor_chat(youtube, chat_id, coll_messages, coll_users, page_token=None):
    request = youtube.liveChatMessages().list(
        liveChatId=chat_id,
        part="snippet",
        pageToken=page_token
    )
    response = request.execute()
    next_page_token = response['nextPageToken']

    write_data_to_db(response['items'], coll_messages, coll_users)

    time.sleep(10)
    monitor_chat(youtube, chat_id, coll_messages, coll_users, page_token=next_page_token)


def write_data_to_db(items, coll_messages, coll_users):
    messages = []
    for item in items:
        messages.append(
            {   
                'timestamp': item['snippet']['publishedAt'], 
                'user_id': item['snippet']['authorChannelId'], 
                'content': item['snippet']['displayMessage']
            }
        )

    if len(messages) > 0:
        obj = coll_messages.insert_many(messages)
        print('Inserted {} messages'.format(len(obj.inserted_ids)))
        write_users_to_db(items, coll_users)


def write_users_to_db(items, collection):
    users = []
    num_users_inserted = 0

    for item in items:
        user_id = item['snippet']['authorChannelId']

        if not collection.find_one({"user_id": user_id}):
            num_users_inserted += 1

            users.append(
                {   
                    'user_id': user_id, 
                    'channel_display_name': None
                }
            )

    if num_users_inserted > 0:
        obj = collection.insert_many(users)
        print('Inserted {} users'.format(num_users_inserted))


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
        forUsername=constants.CHANNEL_NAME
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