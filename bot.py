import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

API_URL = "https://comm-api.game.naver.com/nng_main/v1/community/lounge/Tree_Of_Savior_Neverland/feed"

STATE_FILE = "sent_posts.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_posts():
    r = requests.get(
        API_URL,
        params={
            "boardId": 3,
            "limit": 20,
            "offset": 0,
            "order": "NEW",
        },
        headers=HEADERS,
        timeout=30,
    )

    r.raise_for_status()
    return r.json()["content"]["feeds"]


def load_sent_posts():
    if not os.path.exists(STATE_FILE):
        return set()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_sent_posts(sent_posts):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            list(sent_posts)[-100:],
            f,
            ensure_ascii=False,
            indent=2,
        )


async def get_article(feed_id):

    url = (
        f"https://game.naver.com/lounge/"
        f"Tree_Of_Savior_Neverland/board/detail/{feed_id}"
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        )

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.wait_for_timeout(5000)

        selectors = [
            "[class*='article']",
            "[class*='Article']",
            "[class*='content']",
            "[class*='Content']",
            "[class*='post']",
            "[class*='Post']",
        ]

        best_element = None
        best_length = 0

        for selector in selectors:

            elements = page.locator(selector)

            count = await elements.count()

            for i in range(count):

                element = elements.nth(i)

                try:

                    if not await element.is_visible():
                        continue

                    text = await element.inner_text()

                    length = len(text.strip())

                    if 100 <= length <= 10000:

                        if length > best_length:
                            best_length = length
                            best_element = element

                except Exception:
                    continue

        if best_element:

            # 본문 영역의 텍스트
            content = await best_element.inner_text()

            # 본문 영역의 이미지
            images = await best_element.locator("img").evaluate_all(
                """
                imgs => imgs
                    .map(img => img.src)
                    .filter(src => src && src.startsWith('http'))
                """
            )

        else:

            content = ""
            images = []

        await browser.close()

        return content.strip(), images, url


def clean_content(content, title):

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    # 제목이 본문에 중복으로 들어가는 경우 제거
    cleaned = []

    for line in lines:

        if line == title:
            continue

        # 글 상단 메타정보 제거
        if "북마크 메뉴" in line:
            continue

        if "조회수" in line and len(line) < 200:
            continue

        if "LV " in line and "GM" in line:
            continue

        if "트리오브세이비어:네버랜드 관리자 안내" in line:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def send_discord(title, content, url, image_url=None):

    if len(content) > 3900:
        content = content[:3900] + "\n\n…본문 일부 생략"

    embed = {
        "title": title,
        "url": url,
        "description": content,
    }

    if image_url:
        embed["image"] = {
            "url": image_url
        }

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

    sent_posts = load_sent_posts()

    new_posts = []

    for post in posts:

        feed_id = post.get("feedId")

        if not feed_id:
            continue

        if str(feed_id) not in sent_posts:
            new_posts.append(post)

    # 처음 실행할 때 기존 글을 전부 보내지 않도록 함
    if not os.path.exists(STATE_FILE):

        for post in posts:
            feed_id = post.get("feedId")

            if feed_id:
                sent_posts.add(str(feed_id))

        save_sent_posts(sent_posts)

        print("기존 게시글을 기억했습니다.")
        print("앞으로 새 글이 올라오면 Discord로 전송합니다.")
        return

    # 새 글만 처리
    for post in reversed(new_posts):

        feed_id = post.get("feedId")

        title = post.get(
            "title",
            "트오세 네버랜드 공지"
        )

        print("새 공지 발견:", title)

        content, images, url = asyncio.run(
            get_article(feed_id)
        )

        content = clean_content(
            content,
            title
        )

        if not content:
            content = "본문을 가져오지 못했습니다."

        image_url = images[0] if images else None

        send_discord(
            title,
            content,
            url,
            image_url,
        )

        sent_posts.add(str(feed_id))

        print("Discord 전송 완료:", title)

    save_sent_posts(sent_posts)


if __name__ == "__main__":
    main()
