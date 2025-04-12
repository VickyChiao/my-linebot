from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    LocationMessage,
)

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    LocationMessageContent,
    ImageMessageContent,
    VideoMessageContent,
)

from modules.reply import faq, menu 

import os
import requests

from dotenv import load_dotenv
#從openai模組引入OpenAI模組類別
from openai import OpenAI

load_dotenv()
#是否在rennder.com運行
running_on_render= os.getenv("RENDER")
print("現在是在render上運行嗎?",running_on_render)

if not running_on_render:
      load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_KEY")
)

app = Flask(__name__)

# Line Channel 可於 Line Developer Console 申辦
# https://developers.line.biz/en/

# TODO: 填入你的 CHANNEL_SECRET 與 CHANNEL_ACCESS_TOKEN
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# @app.route() 用以表達伺服器應用程式路由將會對應到 webhooks 的路徑中
@app.route("/", methods=['POST'])
def callback():
    # ====== 以下為接收並驗證 Line Server 傳來訊息的流程，不需更動 ======
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("signature驗證錯誤，請檢查Secret與Access Token是否正確...")
        abort(400)
    return 'OK'

# 此處理器負責處理接收到Line Server傳來的文字訊息時的流程
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入文字訊息時
        print("#" * 30)
        line_bot_api = MessagingApi(api_client)
        user_msg = event.message.text
        print("使用者傳入的文字訊息是:", user_msg)
        
        if user_msg in faq:
            bot_msg = faq[user_msg]
        elif user_msg.lower() in ["menu","選單","主選單"]:
            bot_msg = menu
        else:
            #如果不在上述考慮過的回應,就使用openai回答
            completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role":"system",
                    "content":"""
你是一個講話幽默風趣的AI
回應時,使用繁體中文
使用純文字而不是Markdown格式
"""
                }
            ]
                
           
            )
            print(completion.choices[0].message.content)
            bot_msg = TextMessage(text=completion.choices[0].message.content)

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[bot_msg]
            )
        )

# 此處理器負責處理接收到Line Server傳來的貼圖訊息時的流程
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入貼圖時
        line_bot_api = MessagingApi(api_client)
        sticker_id = event.message.sticker_id
        package_id = event.message.package_id
        keywords_msg = "這張貼圖背後沒有關鍵字"
        if len(event.message.keywords) > 0:
            keywords_msg = "這張貼圖的關鍵字有:"
            keywords_msg += ", ".join(event.message.keywords)
        # 可以使用的貼圖清單
        # https://developers.line.biz/en/docs/messaging-api/sticker-list/
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    StickerMessage(package_id="6325", sticker_id="10979904"),
                    TextMessage(text=f"你剛才傳入了一張貼圖，以下是這張貼圖的資訊:"),
                    TextMessage(text=f"貼圖包ID為 {package_id} ，貼圖ID為 {sticker_id} 。"),
                    TextMessage(text=keywords_msg),
                ]
            )
        )

# 此處理器負責處理接收到Line Server傳來的地理位置訊息時的流程
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入地理位置時
        line_bot_api = MessagingApi(api_client)
        latitude = event.message.latitude
        longitude = event.message.longitude
        address = event.message.address
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"You just sent a location message."),
                    TextMessage(text=f"The latitude is {latitude}."),
                    TextMessage(text=f"The longitude is {longitude}."),
                    TextMessage(text=f"The address is {address}."),
                    LocationMessage(title="Here is the location you sent.", address=address, latitude=latitude, longitude=longitude)
                ]
            )
        )
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        message_id = event.message.id
        
        # Get image content from LINE Messaging API
        headers = {
            'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
        }
        url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Convert image content to base64
            import base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            
            # Send to OpenAI Vision API
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "請用繁體中文描述這張圖片中的內容，描述要簡潔但具體。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                # Get the AI's description
                description = response.choices[0].message.content
                
                # Reply to user with the description
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text=f"我看到的是：\n{description}")
                        ]
                    )
                )
            except Exception as e:
                print(f"Error with OpenAI Vision API: {str(e)}")
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="抱歉，我無法分析這張圖片")
                        ]
                    )
                )
        else:
            print(f"Error getting image content: {response.status_code}")
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="抱歉，無法處理圖片內容")
                    ]
                )
            )

# 此處理器負責處理接收到Line Server傳來的影片訊息時的流程
@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        message_id = event.message.id
        
        # Get video content from LINE Messaging API
        headers = {
            'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
        }
        url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Convert video content to base64
            import base64
            video_base64 = base64.b64encode(response.content).decode('utf-8')
            print(f"Video base64: {video_base64[:100]}...")  # Print first 100 chars of base64
            
            # Reply to user
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=f"收到影片了，影片ID: {message_id}")
                    ]
                )
            )
        else:
            print(f"Error getting video content: {response.status_code}")
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="抱歉，無法處理影片內容")
                    ]
                )
            )

# 如果應用程式被執行執行
if __name__ == "__main__":
    print("[伺服器應用程式開始運行]")
    # 取得遠端環境使用的連接端口，若是在本機端測試則預設開啟於port=5001
    port = int(os.environ.get('PORT', 5001))
    print(f"[Flask即將運行於連接端口:{port}]")
    print(f"若在本地測試請輸入指令開啟測試通道: ./ngrok http {port} ")
    # 啟動應用程式
    # 本機測試使用127.0.0.1, debug=True
    # Heroku部署使用 0.0.0.0
    app.run(host="0.0.0.0", port=port, debug=True)
