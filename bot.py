import os
import asyncio
import requests
from playwright.async_api import async_playwright

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

        # 네이버 페이지가 내용을 불러올 시간을 줌
        await page.wait_for_timeout(5000)

        title = await page.title()

        # 페이지에 실제로 표시된 텍스트 가져오기
        body_text = await page.locator("body").inner_text()

        # 이미지 주소 수집
        images = await page.locator("img").evaluate_all(
            """
            imgs => imgs
                .map(img => img.src)
                .filter(src => src && src.startsWith('http'))
            """
        )

        await browser.close()

        return title, body_text, images, url


def send_discord(title, content, url, image_url=None):
    # 페이지 전체 텍스트에서 너무 긴 부분 제거
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

    post = posts[0]

    feed_id = post.get("feedId")

    print("feedId:", feed_id)

    title, content, images, url = asyncio.run(
        get_article(feed_id)
    )

    print("페이지 제목:", title)
    print("본문 길이:", len(content))
    print("이미지 개수:", len(images))

    send_discord(
        post.get("title", "트오세 네버랜드 공지"),
        content,
        url,
        images[0] if images else None,
    )

    print("Discord 전송 성공!")


if __name__ == "__main__":
    main()
