
import os
import requests
from bs4 import BeautifulSoup
import json
import google.generativeai as genai
import base64
from io import BytesIO
import tweepy
import xml.etree.ElementTree as ET

# 環境変数からAPIキーを取得
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

def get_latest_news_from_bbc():
    """BBC NewsのRSSフィードから最新ニュースを取得する"""
    rss_url = "https://feeds.bbci.co.uk/news/rss.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(rss_url, headers=headers)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
    except requests.exceptions.RequestException as e:
        print(f"Error fetching RSS feed from BBC News: {e}")
        return None

    try:
        root = ET.fromstring(response.content)
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else "No title"
            link = item.find("link").text if item.find("link") is not None else "#"
            description = item.find("description").text if item.find("description") is not None else "No summary available."
            
            if title != "No title" and link != "#":
                return {
                    'title': title,
                    'url': link,
                    'description': description
                }
        return None
    except ET.ParseError as e:
        print(f"Error parsing RSS feed: {e}")
        return None

def generate_analysis_tweet(article_title, article_description):
    """Gemini APIを使用してニュース記事の分析ツイートを生成する"""
    prompt = f"""以下のニュース記事について、専門家のような視点で簡潔に分析し、X (Twitter) で投稿する117文字以内の日本語のツイートを作成してください。絵文字やハッシュタグは含めないでください。\n\n記事タイトル: {article_title}\n記事概要: {article_description}\n\nツイート:"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=150, temperature=0.7),
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        if response.candidates:
            tweet_text = response.candidates[0].content.parts[0].text.strip()
        else:
            print(f"Gemini API did not return any candidates. Finish reason: {response.prompt_feedback.block_reason}")
            return "ニュース分析の生成に失敗しました。"
        
        if len(tweet_text) > 117:
            tweet_text = tweet_text[:114] + "..."
        return tweet_text
    except Exception as e:
        print(f"Error generating analysis tweet with Gemini API: {e}")
        return "ニュース分析の生成に失敗しました。"

def generate_image(text_prompt):
    """DeepAIを使用してAI画像を生成する"""
    try:
        response = requests.post(
            "https://api.deepai.org/api/text2img",
            json={
                'text': text_prompt,
            },
            headers={'api-key': DEEPAI_API_KEY}
        )
        response.raise_for_status()
        image_url = response.json().get('output_url')
        if image_url:
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            return base64.b64encode(image_response.content).decode('utf-8')
        return None
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def post_tweet(tweet_text, news_link, image_base64=None):
    """X (Twitter) にツイートを投稿する"""
    try:
        # X API v2 Clientの初期化
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )

        # X API v1.1 Media Uploadのための認証
        auth_v1_1 = tweepy.OAuth1UserHandler(
            X_CONSUMER_KEY,
            X_CONSUMER_SECRET,
            X_ACCESS_TOKEN,
            X_ACCESS_TOKEN_SECRET
        )
        api_v1_1 = tweepy.API(auth_v1_1)

        media_ids = []
        if image_base64:
            image_data = base64.b64decode(image_base64)
            media = api_v1_1.media_upload(filename="image.png", file=BytesIO(image_data))
            media_ids.append(media.media_id)

        import random
        import string
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        full_tweet_text = f"{tweet_text} {news_link} #{random_string}"

        response = client.create_tweet(text=full_tweet_text, media_ids=media_ids if media_ids else None)
        print(f"Tweet posted successfully! Tweet ID: {response.data['id']}")
    except tweepy.TweepyException as e:
        print(f"Error posting tweet: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during tweet posting: {e}")

def main():
    print("Fetching latest news from BBC News RSS feed...")
    news_article = get_latest_news_from_bbc()

    if news_article:
        print(f"News fetched: {news_article['title']}")
        tweet_analysis = generate_analysis_tweet(news_article['title'], news_article['description'])
        
        print(f"Generated tweet analysis: {tweet_analysis}")

        # DeepAIの支払い問題のため、画像生成を一時的に無効化
        # print("Generating AI image...")
        # image_base64 = generate_image(tweet_analysis)

        # if image_base64:
        #     print("AI image generated. Posting tweet with image...")
        #     post_tweet(tweet_analysis, news_article["url"], image_base64)
        # else:
        #     print("Failed to generate AI image. Posting tweet without image...")
        #     post_tweet(tweet_analysis, news_article["url"]) 
        
        # DeepAIを無効化しているため、画像なしでツイートを投稿
        post_tweet(tweet_analysis, news_article["url"])
    else:
        print("No news article found from BBC News RSS feed.")

if __name__ == "__main__":
    main()

