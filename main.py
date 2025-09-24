
import os
import requests
import tweepy
import google.generativeai as genai
from datetime import datetime

# 環境変数の設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

genai.configure(api_key=GEMINI_API_KEY)

from newsapi import NewsApiClient

def get_latest_reuters_news():
    """NewsAPI.orgからロイターの最新ニュースを取得する"""
    newsapi_key = os.getenv("NEWSAPI_API_KEY")
    if not newsapi_key:
        print("NEWSAPI_API_KEYが設定されていません。")
        return Non    newsapi = NewsApiClient(api_key=newsapi_key)

    newsapi = NewsApiClient(api_key=newsapi_key)

    try:
        sources_response = newsapi.get_sources(language='en', country='us')
        if sources_response['status'] != 'ok':
            print(f"NewsAPI sources error: {sources_response}")
            return None     for source in sources_response['sources']:
            if source['name'] == 'Reuters':
                reuters_source_id = source['id']
                break

        if not reuters_source_id:
            print("NewsAPIからReutersのソースIDが見つかりませんでした。")
            return None

        top_headlines = newsapi.get_top_headlines(sources=reuters_source_id, language='en')
        if top_headlines['status'] != 'ok':
            print(f"NewsAPI top headlines error: {top_headlines}")
            return None

        print(f"NewsAPI response status: {top_headlines['status']}")
        print(f"NewsAPI total results: {top_headlines['totalResults']}")
        print(f"NewsAPI articles: {top_headlines['articles']}")

        if top_headlines['articles']:
            article = top_headlines['articles'][0] # 最初の記事を使用
            news_data = {
                "title": article['title'] if article['title'] else "No Title",
                "link": article['url'] if article['url'] else "#",
                "description": article['description'] if article['description'] else article['title']
            }
            print(f"Returning news data: {news_data}")
            return news_data
        else:
            print("NewsAPIから記事が取得できませんでした。")
            return None:
        print(f"ニュース取得エラー: {e}")
        return None

def generate_analysis_and_image_prompt(news_title, news_description):
    """Gemini APIを使って分析ツイート本文と画像生成プロンプトを生成する"""
    model = genai.GenerativeModel('gemini-pro') # テキスト生成用
    image_model = genai.GenerativeModel('gemini-pro-vision') # 画像生成プロンプト用

    # 分析ツイート本文の生成
    prompt_text = f"""以下のロイターニュースのタイトルと概要を元に、専門家がコメントするような形式で、全角140文字以内のツイート本文を作成してください。ニュースのリンクは含めないでください。\n\nタイトル: {news_title}\n概要: {news_description}\n\nツイート本文:"""
    response_text = model.generate_content(prompt_text)
    tweet_text = response_text.text.strip()

    # 画像生成プロンプトの生成
    prompt_image = f"""以下のニュース内容を象徴するような画像を生成するための英語のプロンプトを生成してください。\n\nニュースタイトル: {news_title}\nニュース概要: {news_description}\n\n画像生成プロンプト (英語):"""
    response_image = model.generate_content(prompt_image)
    image_prompt = response_image.text.strip()

    return tweet_text, image_prompt

def generate_image_with_deepai(image_prompt, output_path="news_image.png"):
    """DeepAI APIを使って画像を生成する"""
    deepai_api_key = os.getenv("DEEPAI_API_KEY")
    if not deepai_api_key:
        print("DEEPAI_API_KEYが設定されていません。")
        return None

    r = requests.post(
        "https://api.deepai.org/api/text2img",
        data={
            "text": image_prompt,
        },
        headers={
            "api-key": deepai_api_key,
        }
    )
    if r.status_code == 200:
        try:
            image_url = r.json()["output_url"]
            img_data = requests.get(image_url).content
            with open(output_path, "wb") as handler:
                handler.write(img_data)
            print(f"画像を生成しました: {output_path}")
            return output_path
        except Exception as e:
            print(f"DeepAIからの画像URL処理エラー: {e}")
            return None
    else:
        print(f"DeepAI APIエラー: {r.status_code} - {r.text}")
        return None

def post_tweet(tweet_text, news_link, image_path=None):
    """Xにツイートを投稿する"""
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )

        media_ids = []
        if image_path and os.path.exists(image_path):
            # 画像をアップロードする (v1.1 APIを使用)
            auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
            api = tweepy.API(auth)
            media = api.media_upload(image_path)
            media_ids.append(media.media_id)

        full_tweet_text = f"{tweet_text}\n{news_link}"
        # 140文字制限の確認 (全角文字は2文字としてカウントされる場合があるため、より厳密なチェックが必要)
        # ここでは簡易的に文字数でチェック
        if len(full_tweet_text) > 140:
            # リンクを短縮するなどして調整が必要
            # 今回はGeminiに140文字以内を指示しているので、超過した場合は警告を出す
            print(f"警告: ツイート本文が140文字を超過しています。調整してください。現在の文字数: {len(full_tweet_text)}")
            # 超過分を切り詰めるなどの処理も検討
            full_tweet_text = full_tweet_text[:137] + "..." # リンク分を考慮して短縮

        response = client.create_tweet(text=full_tweet_text, media_ids=media_ids if media_ids else None)
        print(f"ツイート成功: {response.data['id']}")
        return True
    except tweepy.TweepyException as e:
        print(f"ツイートエラー: {e}")
        return False



def main():
    news = get_latest_reuters_news()
    if news:
        tweet_text, image_prompt = generate_analysis_and_image_prompt(news["title"], news["description"])
        
        image_path = generate_image_with_deepai(image_prompt)


        if tweet_text and news["link"]:
            post_tweet(tweet_text, news["link"], image_path)
        else:
            print("ツイート本文またはニュースリンクが生成できませんでした。")
    else:
        print("ニュースを取得できませんでした。")

if __name__ == "__main__":
    main()


