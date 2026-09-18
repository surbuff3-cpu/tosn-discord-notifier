import os
import json
import html
import re
import requests
from bs4 import BeautifulSoup

LOUNGE_ID = "Tree_Of_Savior_Neverland"
BOARD_ID = 3

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

API_URL = f"https://comm-api.game.naver.com/nng_main/v1/community/lounge/{LOUNGE_ID}/feed"
DETAIL_URL = f"https://comm-api.game.naver.com/nng_main/v1/community/lounge/{LOUNGE_ID}/feed/{{feed_id}}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_posts():
    response = requests.get(
        API_URL,
        params={
            "boardId": BOARD_ID,
            "buffFilteringYN": "N",
            "limit": 30,
            "offset": 0,
            "order": "NEW",
        },
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    return data["content"]["feeds"]


def get_detail(feed_id):
    response = requests.get(
        DETAIL_URL.format(feed_id=feed_id),
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()
    return response.json()


def clean_html(value):
    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    return soup.get_text("\n", strip=True)


def send_discord(title, content, url):
    content = clean_html(content)

    if len(content) > 3900:
        content = content[:3900] + "\n\n…본문이 길어 일부만 표시됩니다."

    payload = {
        "embeds": [
            {
                "title": title,
                "url": url,
                "description": content,
            }
        ]
    }

    response = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=20,
    )

    response.raise_for_status()


def main():
    posts = get_posts()

    for post in posts[:3]:
        feed_id = post.get("feedId")

        if not feed_id:
            continue

        detail = get_detail(feed_id)

        feed = detail.get("content", {}).get("feed", detail.get("content", {}))

        title = feed.get("title") or post.get("title") or "트오세 네버랜드 공지"

        content = (
            feed.get("contents")
            or feed.get("content")
            or ""
        )

        url = f"https://game.naver.com/lounge/{LOUNGE_ID}/board/detail/{feed_id}"

        print(title)
        print(url)

        # 첫 테스트에서는 실제 전송을 하지 않습니다.
        print(clean_html(content)[:500])


if __name__ == "__main__":
    main()
