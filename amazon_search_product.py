import asyncio
import json
import random
import re
import scrapy
from urllib.parse import urljoin
import httpx
from fake_useragent import UserAgent
from scrapy.http import HtmlResponse

class AmazonSearchProductSpider(scrapy.Spider):
    name = "amazon_search_product"

    async def fetch_url(self, url, headers):
        async with httpx.AsyncClient(headers=headers) as client:
            return await client.get(url)

    async def parse(self, response):
        pass  # Placeholder for the parse method, you can implement it as needed

    def start_requests(self):
        keyword_list = ['ipad']
        user_agent = UserAgent()

        # Headers for ScrapeOps
        scrapeops_headers = {
            'x-api-key': 'b497a621-cb51-4f88-9115-b89f6d0dd79d',
        }

        headers = {
            'User-Agent': user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        for keyword in keyword_list:
            amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page=1'
            yield scrapy.Request(url=amazon_search_url, callback=self.discover_product_urls, headers=headers, meta={'keyword': keyword, 'page': 1, 'scrapeops_headers': scrapeops_headers})

    async def discover_product_urls(self, response):
        print(f"Discovering product URLs for page {response.meta['page']} of {response.meta['keyword']}")
        page = response.meta['page']
        keyword = response.meta['keyword']
        headers = response.request.headers
        scrapeops_headers = response.meta.get('scrapeops_headers', {})
        print(f"Finished discovering product URLs for page {response.meta['page']} of {response.meta['keyword']}")

        # Discover Product URLs
        search_products = response.css(
            "div.s-result-item[data-component-type=s-search-result]")
        for product in search_products:
            relative_url = product.css("h2>a::attr(href)").get()
            product_url = urljoin('https://www.amazon.com/',
                                  relative_url).split("?")[0]

            yield scrapy.Request(url=product_url, callback=self.parse_product_data, headers=headers, meta={'keyword': keyword, 'page': page, 'scrapeops_headers': scrapeops_headers})

        if page == 1:
            available_pages = response.xpath(
                '//*[contains(@class, "s-pagination-item")][not(has-class("s-pagination-separator"))]/text()'
            ).getall()

            last_page = available_pages[-1]
            for page_num in range(2, int(last_page) + 1):
                amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page={page_num}'
                yield scrapy.Request(url=amazon_search_url, callback=self.discover_product_urls, headers=headers, meta={'keyword': keyword, 'page': page_num, 'scrapeops_headers': scrapeops_headers})

    async def parse_product_data(self, response, **kwargs):
        scrapeops_headers = kwargs.get('scrapeops_headers', {})
        await asyncio.sleep(random.uniform(1, 3))
        # Extracting data using CSS selectors
        name = response.css("#productTitle::text").get("").strip()
        price = response.css('span#priceblock_ourprice::text, span#priceblock_dealprice::text').get("").strip()
        if not price:
            price = response.css('.a-price span[aria-hidden="true"] ::text').get("")
            if not price:
                price = response.css('.a-price .a-offscreen ::text').get("")

        feature_bullets = response.css("#feature-bullets li ::text").getall()
        image_data = response.css("img#landingImage::attr(src)").get()
        variant_data = response.css("div#variation_color_name span.selection::text").getall()

        # Additional data extraction using regular expressions
        image_data = json.loads(re.findall(r"colorImages':.*'initial':\s*(\[.+?\])},\n", response.text)[0])
        variant_data = re.findall(r'dimensionValuesDisplayData"\s*:\s* ({.+?}),\n', response.text)

        yield {
            "name": name,
            "price": price,
            "feature_bullets": feature_bullets,
            "images": {"main": image_data},
            "variant_data": [{"color": variant} for variant in variant_data],
        }
