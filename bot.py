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


def get_article(feed_id):
    url = (
        f"https://game.naver.com/lounge/"
        f"Tree_Of_Savior_Neverland/board/detail/{feed_id}"
    )

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # 페이지에서 본문으로 보이는 영역 찾기
    candidates = []

    for tag in soup.find_all(["article", "div", "section"]):
        text = tag.get_text("\n", strip=True)

        if len(text) >= 100:
            candidates.append((len(text), tag))

    if candidates:
        # 너무 큰 페이지 전체 영역은 제외하고 적당한 영역 선택
        candidates.sort(key=lambda x: x[0])

        for length, tag in candidates:
            if length <= 10000:
                content = tag.get_text("\n", strip=True)
                if content:
                    return content, tag

    return "본문을 가져오지 못했습니다.", soup


def send_discord(title, content, url, image_url=None):
    # Discord embed 설명은 너무 길면 잘라냄
    if len(content) > 3900:
        content = content[:3900] + "\n\n…본문 일부 생략"

    embed = {
        "title": title,
        "url": url,
        "description": content,
    }

    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "embeds": [embed]
    }

    r = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=30,
    )

    r.raise_for_status()


def main():
    posts = get_posts()

    if not posts:
        print("게시글을 찾지 못했습니다.")
        return

    post = posts[0]

    title = post.get("title", "트오세 네버랜드 공지")
    feed_id = post.get("feedId")

    url = (
        f"https://game.naver.com/lounge/"
        f"Tree_Of_Savior_Neverland/board/detail/{feed_id}"
    )

    print("공지:", title)
    print("주소:", url)

    content, article = get_article(feed_id)

    # 본문에 들어있는 첫 번째 이미지 찾기
    image_url = None

    for img in article.find_all("img"):
        src = img.get("src") or img.get("data-src")

        if src and src.startswith("http"):
            image_url = src
            break

    send_discord(
        title,
        content,
        url,
        image_url,
    )

    print("Discord 전송 성공!")


if __name__ == "__main__":
    main()
