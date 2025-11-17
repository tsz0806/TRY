# ================================
# 第一部分：匯入必要的函式庫
# ================================

from fastapi import FastAPI  # FastAPI 框架，用於建立 Web API
from fastapi.middleware.cors import CORSMiddleware  # CORS 中介軟體，允許跨網域請求
from pydantic import BaseModel  # 資料驗證函式庫，定義請求/回應的資料模型
from typing import Optional, Dict, Any  # 型別提示，讓程式碼更清楚
import requests  # HTTP 客戶端函式庫，用於向 Grok 網站發送請求
import json  # JSON 處理函式庫
import uuid  # 產生唯一 ID
import logging  # 日誌記錄

# 設定日誌系統，層級設為 INFO（會顯示一般資訊）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# 第二部分：建立 FastAPI 應用程式
# ================================

app = FastAPI(
    title="Grok Mirror API",  # API 名稱
    version="3.3.0"  # 版本號
)

# 新增 CORS 中介軟體
# 作用：允許任何網站呼叫這個 API（Dify 需要這個功能）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源（正式環境應該限制）
    allow_credentials=True,  # 允許發送 Cookie
    allow_methods=["*"],  # 允許所有 HTTP 方法（GET, POST 等）
    allow_headers=["*"],  # 允許所有 HTTP 標頭
)

# ================================
# 第三部分：關鍵設定（從 F12 取得）
# ================================

GROK_BASE_URL = "https://grok.ylsagi.com"  # Grok 鏡像網站的基礎 URL

# ⭐⭐⭐ 重點！這些都是從 F12 開發者工具擷取的 ⭐⭐⭐
HEADERS = {
    "Content-Type": "application/json",  # 標準 HTTP 標頭
    
    # 🔑 來源：F12 → Network → 選擇請求 → Request Headers → Cookie
    # 作用：身分驗證，證明你已經登入
    # 如何取得：
    #   1. 在 Grok 網站發送訊息
    #   2. 按 F12 開啟開發者工具
    #   3. Network 標籤 → 找到 responses 請求
    #   4. Headers 標籤 → Request Headers → 複製 Cookie 那一整行
    "Cookie": 'share_token=aaf6c70a7ba8832ae9b09ac055cd1081947d2d897b3ca2b65d826ceeecbcf653; imgID=67e253bdd0b63c582005f9a7; i18nextLng=en; mp_ea93da913ddb66b6372b89d97b1029ac_mixpanel=%7B%22distinct_id%22%3A%2200a70e22-fed7-4713-b4c5-9b16ba9c856f%22%2C%22%24device_id%22%3A%229c284b9a-2aa5-4b8e-886e-78017fc21d9e%22%2C%22%24initial_referrer%22%3A%22https%3A%2F%2Fylsagi.com%2F%22%2C%22%24initial_referring_domain%22%3A%22ylsagi.com%22%2C%22__mps%22%3A%7B%7D%2C%22__mpso%22%3A%7B%7D%2C%22__mpus%22%3A%7B%7D%2C%22__mpa%22%3A%7B%7D%2C%22__mpu%22%3A%7B%7D%2C%22__mpr%22%3A%5B%5D%2C%22__mpap%22%3A%5B%5D%2C%22%24user_id%22%3A%2200a70e22-fed7-4713-b4c5-9b16ba9c856f%22%7D',
    
    # 🔑 來源：F12 → Request Headers → User-Agent
    # 作用：偽裝成瀏覽器，避免被識別為機器人
    # 如何取得：在 F12 的 Request Headers 中直接複製
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
    
    # 🔑 來源：F12 → Request Headers → Origin 和 Referer
    # 作用：告訴伺服器請求來自哪裡
    "Origin": "https://grok.ylsagi.com",
    "Referer": "https://grok.ylsagi.com/",
}

# ================================
# 第四部分：資料模型定義
# ================================

class ChatRequest(BaseModel):
    """
    定義客戶端（如 Dify）發送給這個 API 的請求格式
    
    範例：
    {
        "message": "你好",
        "model": "grok-3"
    }
    """
    message: str  # 必需：使用者的問題
    model: Optional[str] = "grok-3"  # 可選：使用的模型，預設 grok-3

class ChatResponse(BaseModel):
    """
    定義這個 API 回傳給客戶端的回應格式
    
    成功範例：
    {
        "success": true,
        "data": {
            "response": "你好！",
            "conversation_id": "...",
            "response_id": "..."
        },
        "error": null
    }
    
    失敗範例：
    {
        "success": false,
        "data": null,
        "error": "Cookie 過期"
    }
    """
    success: bool  # 是否成功
    data: Optional[Dict[str, Any]] = None  # 成功時的資料
    error: Optional[str] = None  # 失敗時的錯誤訊息

# ================================
# 第五部分：建構請求負載
# ================================

def build_payload(message: str, model: str = "grok-3") -> dict:
    """
    建構發送給 Grok 網站的請求本體
    
    ⭐⭐⭐ 這個結構也是從 F12 取得的 ⭐⭐⭐
    
    如何取得：
    1. 在 Grok 網站發送訊息 "測試"
    2. F12 → Network → 找到 POST .../conversations/new
    3. 點擊 → Payload 標籤（或 Request 標籤）
    4. 複製整個 JSON 結構
    
    參數：
        message: 使用者的問題
        model: 使用的模型名稱
    
    回傳：
        一個包含所有必要參數的字典
    """
    return {
        # 以下所有欄位都來自 F12 → Payload 標籤
        "disableMemory": False,  # 不停用記憶功能
        "disableSearch": False,  # 不停用搜尋功能
        "disableSelfHarmShortCircuit": False,
        "disableTextFollowUps": False,
        "enableImageGeneration": True,  # 啟用圖片生成
        "enableImageStreaming": True,
        "enableSideBySide": True,
        "fileAttachments": [],  # 檔案附件（空陣列）
        "forceConcise": False,
        "forceSideBySide": False,
        "imageAttachments": [],  # 圖片附件（空陣列）
        "imageGenerationCount": 2,
        "isAsyncChat": False,
        "isReasoning": False,
        "message": message,  # ⭐ 使用者的問題（唯一動態的欄位）
        "modelMode": "MODEL_MODE_AUTO",
        "modelName": model,  # ⭐ 模型名稱
        "responseMetadata": {},
        "modelConfigOverride": {},
        "modelMap": {},
        "requestModelDetails": {
            "modelId": model  # 模型 ID
        },
        "returnImageBytes": False,
        "returnRawGrokInXaiRequest": False,
        "sendFinalMetadata": True,
        "temporary": False,  # 不是暫時對話
        "toolOverrides": {}
    }

# ================================
# 第六部分：解析串流式回應
# ================================

def parse_streaming_response(response) -> Dict[str, Any]:
    """
    解析 Grok 回傳的串流式回應
    
    為什麼需要這個函式？
    - Grok 不是一次性回傳完整回覆
    - 而是像打字機一樣一個字一個字地發送（串流式回應）
    - 我們需要逐行讀取並拼接
    
    ⭐⭐⭐ 回應格式也是從 F12 觀察得出 ⭐⭐⭐
    
    如何觀察：
    1. F12 → Network → 找到 responses 請求
    2. 點擊 → Response 標籤
    3. 會看到很多行 JSON，每行一個物件
    
    回應範例：
    {"result":{"conversation":{"conversationId":"..."}}}
    {"result":{"response":{"token":"你"}}}
    {"result":{"response":{"token":"好"}}}
    {"result":{"response":{"isSoftStop":true}}}
    
    參數：
        response: requests 函式庫回傳的 Response 物件
    
    回傳：
        包含完整回覆文字、對話ID、回應ID 的字典
    """
    full_response = ""  # 儲存完整的回覆文字
    response_id = None  # 回應 ID
    conversation_id = None  # 對話 ID
    line_count = 0  # 處理的行數（用於除錯）
    
    logger.info("開始解析串流式回應...")
    
    try:
        # 逐行讀取回應
        for line in response.iter_lines():
            if line:  # 跳過空行
                line_count += 1
                try:
                    # 將位元組解碼為字串
                    line_str = line.decode('utf-8')
                    
                    # 記錄前5行（用於除錯）
                    if line_count <= 5:
                        logger.info(f"Line {line_count}: {line_str[:200]}")
                    
                    # 將 JSON 字串解析為 Python 字典
                    data = json.loads(line_str)
                    
                    # 檢查是否包含 "result" 鍵
                    if "result" in data:
                        result = data["result"]
                        
                        # ===== 方法1：從巢狀的 response 物件提取 =====
                        # ⭐ 透過 F12 觀察到資料結構是巢狀的
                        # 實際結構：result → response → token/responseId 等
                        if "response" in result:
                            inner_response = result["response"]
                            
                            # 提取 token（一個字或詞）
                            if "token" in inner_response:
                                token = inner_response["token"]
                                if token:
                                    full_response += token  # 拼接到完整回覆
                                    logger.debug(f"Found token: {token}")
                            
                            # 提取回應 ID
                            if "responseId" in inner_response:
                                response_id = inner_response["responseId"]
                            
                            # 檢查是否有完整訊息（有時會直接回傳完整文字）
                            if "modelResponse" in inner_response:
                                model_resp = inner_response["modelResponse"]
                                if "message" in model_resp:
                                    full_response = model_resp["message"]
                                    logger.info(f"Got full message: {full_response[:100]}")
                                if "responseId" in model_resp:
                                    response_id = model_resp["responseId"]
                            
                            # 檢查是否結束（isSoftStop: true 表示回應完成）
                            if inner_response.get("isSoftStop", False):
                                logger.info("Received soft stop")
                                break  # 停止讀取
                        
                        # ===== 方法2：提取對話 ID =====
                        # 從第一行的 conversation 物件中取得
                        if "conversation" in result:
                            conv = result["conversation"]
                            if "conversationId" in conv:
                                conversation_id = conv["conversationId"]
                                logger.info(f"Got conversationId: {conversation_id}")
                        
                        # ===== 方法3：相容舊格式（直接在 result 下） =====
                        # 某些版本的 API 可能直接把 token 放在 result 層級
                        if "token" in result:
                            token = result["token"]
                            if token:
                                full_response += token
                        
                        if "conversationId" in result:
                            conversation_id = result["conversationId"]
                        
                        if "responseId" in result:
                            response_id = result["responseId"]
                
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    continue  # 跳過無法解析的行
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")
                    continue
        
        logger.info(f"Parsing completed. Lines: {line_count}, Response length: {len(full_response)}")
        
    except Exception as e:
        logger.error(f"Error during iteration: {e}")
    
    # 回傳解析結果
    return {
        "response": full_response,  # 完整的回覆文字
        "response_id": response_id,  # 回應 ID（用於多輪對話）
        "conversation_id": conversation_id,  # 對話 ID
        "debug_line_count": line_count  # 處理的行數（除錯用）
    }

# ================================
# 第七部分：API 路由端點
# ================================

@app.get("/")
async def root():
    """
    根路徑，訪問 https://xxx.hf.space/ 時回傳的內容
    用途：檢查 API 是否在運行
    """
    return {
        "name": "Grok Mirror API",
        "version": "3.3.0 - Fixed nested response",
        "status": "running"
    }

@app.get("/health")
async def health():
    """
    健康檢查端點
    用途：讓 Dify 或其他服務檢查 API 是否正常
    """
    return {"status": "healthy"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    核心聊天端點 - 這是 Dify 呼叫的主要介面
    
    流程：
    1. 接收來自 Dify 的請求（包含使用者問題）
    2. 將請求轉發給 Grok 網站
    3. 解析 Grok 的串流式回應
    4. 回傳給 Dify
    
    參數：
        request: ChatRequest 物件，包含使用者的問題
    
    回傳：
        ChatResponse 物件，包含 Grok 的回覆或錯誤訊息
    """
    try:
        # 檢查訊息是否為空
        if not request.message:
            return ChatResponse(success=False, error="Message is required")
        
        logger.info(f"收到請求: {request.message}")
        
        # ⭐ 來源：F12 → Network → 請求的 URL
        # 構建 Grok API 的完整 URL
        # 這個端點會同時建立新對話並發送第一條訊息
        url = f"{GROK_BASE_URL}/rest/app-chat/conversations/new"
        
        # 構建請求本體
        payload = build_payload(request.message, request.model)
        
        # 準備請求標頭
        headers = HEADERS.copy()  # 複製基礎 headers
        
        # 🔑 來源：F12 → Request Headers → x-xai-request-id
        # 每次請求都需要一個唯一 ID
        # 使用 uuid.uuid4() 產生隨機的唯一識別碼
        headers["x-xai-request-id"] = str(uuid.uuid4())
        
        # 🔑 來源：F12 → Request Headers → x-statsig-id
        # 分析追蹤 ID（從瀏覽器請求中複製）
        # 這是用於統計和分析的識別碼
        headers["x-statsig-id"] = "JdqGp+hE6q0WsMpDDLRldv0O6ZNb+Mny24KLm/R/9pJdezRyT5a+PbxEdMFEOTVSTrW47iG05JO2DhUM3iJUk/pqbz4SJg"
        
        logger.info(f"發送請求到: {url}")
        
        # 發送 POST 請求到 Grok 網站
        response = requests.post(
            url,
            headers=headers,  # 包含 Cookie 等認證資訊
            json=payload,  # 請求本體（使用者問題等）
            stream=True,  # ⭐ 重要：啟用串流式接收
            timeout=60  # 逾時時間 60 秒
        )
        
        logger.info(f"收到回應，狀態碼: {response.status_code}")
        
        # 檢查 HTTP 狀態碼
        if response.status_code == 200:
            # 解析串流式回應
            result = parse_streaming_response(response)
            
            logger.info(f"解析結果: response_length={len(result.get('response', ''))}, line_count={result.get('debug_line_count', 0)}")
            
            # 檢查是否成功提取到回覆
            if not result.get("response"):
                return ChatResponse(
                    success=False,
                    error="No response text extracted",
                    data={
                        "debug_info": {
                            "lines_processed": result.get("debug_line_count", 0),
                            "response_id": result.get("response_id"),
                            "conversation_id": result.get("conversation_id"),
                            "hint": "檢查 Logs 取得詳細資訊"
                        }
                    }
                )
            
            # 成功：回傳 Grok 的回覆
            return ChatResponse(
                success=True,
                data={
                    "response": result.get("response", ""),
                    "conversation_id": result.get("conversation_id"),
                    "response_id": result.get("response_id")
                }
            )
        else:
            # HTTP 錯誤（如 401, 403, 500 等）
            error_text = response.text[:200]
            logger.error(f"HTTP錯誤 {response.status_code}: {error_text}")
            return ChatResponse(
                success=False,
                error=f"Request failed with status {response.status_code}",
                data={"details": error_text}
            )
            
    except requests.Timeout:
        # 請求逾時
        logger.error("請求逾時")
        return ChatResponse(success=False, error="Request timeout")
    except Exception as e:
        # 其他未知錯誤
        logger.error(f"未知錯誤: {str(e)}", exc_info=True)
        return ChatResponse(success=False, error=f"Error: {str(e)}")

# ================================
# 第八部分：啟動伺服器
# ================================
if __name__ == "__main__":
    import uvicorn
    import os
    # Koyeb 會提供 PORT 環境變數
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
