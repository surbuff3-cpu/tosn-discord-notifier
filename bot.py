import os
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

API_URL = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Tree_Of_Savior_Neverland/feed"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_posts():
    r = requests.get(
        API_URL,
        params={
            "boardId": 3,
            "limit": 5,
            "offset": 0,
            "order": "NEW",
        },
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["content"]["feeds"]


def send_test(post):
    title = post.get("title", "트오세 네버랜드 공지")
    feed_id = post.get("feedId")

    url = (
        f"https://game.naver.com/lounge/"
        f"Tree_Of_Savior_Neverland/board/detail/{feed_id}"
    )

    message = {
        "embeds": [
            {
                "title": title,
                "url": url,
                "description": "네이버 게임 라운지 공지 감지 테스트입니다.",
            }
        ]
    }

    r = requests.post(
        DISCORD_WEBHOOK,
        json=message,
        timeout=30,
    )
    r.raise_for_status()


def main():
    posts = get_posts()

    if not posts:
        print("게시글을 찾지 못했습니다.")
        return

    print("게시글 확인:", posts[0].get("title"))

    send_test(posts[0])

    print("Discord 테스트 전송 성공!")


if __name__ == "__main__":
    main()
