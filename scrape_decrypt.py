import logging
import random
import pandas as pd
import time
import requests
from dotenv import load_dotenv
import http.client, urllib.parse
import os
import json
from datetime import datetime, timezone

load_dotenv(".env", override=True)
pushover_api_key = os.environ['MY_PUSHOVER_API_KEY']
pushover_user_key = os.environ['MY_WORK_PUSHOVER_USER_KEY']
proxy = os.environ['PROXY']
proxies = {
    "http": proxy,
    "https": proxy,
}

def send_pushover_alert(message, priority=0, user_key=pushover_user_key):
    if priority == 2:
        sound = "persistent"
    else:
        sound = "tugboat"

    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.parse.urlencode({
                     "token": pushover_api_key,
                     "user": user_key,
                     "message": message,
                     "priority": priority,
                     "retry": 30,
                     "expire": 600,
                     "sound": sound,
                 }), {"Content-type": "application/x-www-form-urlencoded"})
    print(conn.getresponse().read())
    return None

url = "https://gateway.decrypt.co"
headers = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://decrypt.co",
    "priority": "u=1, i",
    "referer": "https://decrypt.co",
    "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}


def fetch_posts():
    payload = {
        "query": """
        {
          articles(
            filters: {
              status: { eq: FUTURE },
              locale: { eq: "en" }
            },
            pagination: { page: 1, pageSize: 5 },
            sort: ["publishedAt:desc"]
          ) {
            data {
              id
              title
              slug
              publishedAt
            }
          }
        }
        """
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def fetch_post(post_id):
    payload = {
        "operationName": "GetPost",
        "variables": {
            "id": post_id
        },
        "query": """
        query GetPost($id: PositiveInt!) {
          article(
            id: $id
          ) {
            data {
              id
              status
              locale
              title
              sponsor {
                name
                url
              }
              excerpt
              blurb
              slug
              publishedAt
              modifiedAt
            }
          }
        }
        """
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def check_future_posts(lookahead=50):
    logging.basicConfig(
        filename='./data/decrypt.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    while True:
        results = []
        try:
            posts_data = fetch_posts()
            ids = [
                int(p["id"]) for p in posts_data["data"]["articles"]["data"]
                if "id" in p
            ]
            max_id = max(ids)
            logging.info(f"Latest known post ID: {max_id}")

            for test_id in range(max_id + 1, max_id + 1 + lookahead):
                time.sleep(1)
                data = fetch_post(test_id)
                post = data["data"]["article"]["data"]
                logging.info(f"Tried post {test_id}: result was {post}")
                if post is not None:
                    results.append(post)
                    status = post["status"]

                    if status != 'PUBLISH':
                        msg = f"⏳ Future Decrypt article found! ID {post['id']} {post['status']} {post['publishedAt']} - {post['title']}"
                        send_pushover_alert(msg, priority=2)
                        print(msg)
                        logging.info(msg)
                    else:
                        msg = f"Decrypt article found! ID {post['id']} {post['status']} {post['publishedAt']} - {post['title']}"
                        send_pushover_alert(msg, priority=1)
                        print(msg)
                        logging.info(msg)
        except Exception as e:
            msg = f'Decrypt call failed because {e}'
            logging.error(msg)
            send_pushover_alert(msg, priority=-1)
            time.sleep(60)


if __name__ == "__main__":
    check_future_posts(lookahead=60)