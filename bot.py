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

        await page.wait_for_timeout(5000)

        # 네이버 게임 라운지에서 본문으로 사용되는 요소들을 찾음
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

                    # 너무 짧거나 페이지 전체에 가까운 영역은 제외
                    if 100 <= length <= 10000:

                        if length > best_length:
                            best_length = length
                            best_element = element

                except Exception:
                    continue

        if best_element:

            content = await best_element.inner_text()

            images = await best_element.locator("img").evaluate_all(
                """
                imgs => imgs
                    .map(img => img.src)
                    .filter(src => src && src.startsWith('http'))
                """
            )

        else:

            content = "본문 영역을 찾지 못했습니다."

            images = []

        await browser.close()

        return content.strip(), images, url


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

    post = posts[0]

    feed_id = post.get("feedId")

    title = post.get(
        "title",
        "트오세 네버랜드 공지"
    )

    print("공지:", title)
    print("feedId:", feed_id)

    content, images, url = asyncio.run(
        get_article(feed_id)
    )

    print("본문 길이:", len(content))
    print("본문 이미지:", len(images))

    send_discord(
        title,
        content,
        url,
        images[0] if images else None,
    )

    print("Discord 전송 성공!")


if __name__ == "__main__":
    main()
