# 我獨自生肌 Backend – Quick API Guide (for Flutter)

輕量版說明，讓前端可以快速串接。  
後端技術棧：**FastAPI + MySQL + JWT（Access / Refresh Token）**

---

## 1. 啟動方式

### 1.1 環境需求

- Python 3.10+
- MySQL（已建立好 `chicken_db` 等資料表）
- 已安裝專案相依套件（例如）：

```bash
cd chicken_backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.2 啟動 FastAPI 伺服器

```bash
uvicorn main:app --reload --port 8000
```

啟動後，主要 Base URL 為：

```text
http://127.0.0.1:8000
```

Swagger 文件（可測試 API）：

```text
http://127.0.0.1:8000/docs
```

---

## 2. 認證機制概觀

除了 `/auth/*` 以外的 API，**全部都需要**：

```http
Authorization: Bearer <access_token>
```

### 2.1 遊客登入（Guest Login）

**POST** `/auth/guest`

- Request JSON：

```json
{
  "platform": "android",
  "app_version": "1.0.0",
  "device_id": "optional-device-id-or-null"
}
```

- Response JSON（重點欄位）：

```json
{
  "user_id": 15,
  "access_token": "<JWT>",
  "expires_in": 3600,
  "is_guest": true,
  "refresh_token": "<REFRESH>",
  "refresh_expires_in": 2592000
}
```

> ✅ Flutter 要做的事：  
> - 第一次登入：呼叫 `/auth/guest`，儲存 `access_token` & `refresh_token` & `device_id`（若有）。  
> - 之後啟動 App 時帶同一個 `device_id`，就會回到同一個 user。

---

### 2.2 更新 Access Token

**POST** `/auth/refresh`

- Request JSON：

```json
{
  "refresh_token": "<REFRESH>"
}
```

- Response JSON：

```json
{
  "access_token": "<NEW_JWT>",
  "expires_in": 3600
}
```

> Flutter 流程建議：  
> - 若 API 回傳 401，可以用 `refresh_token` 撈新的 `access_token`，再重送一次請求。  
> - 若 refresh 也失敗 → 重新呼叫 `/auth/guest`。

---

## 3. 共通資料格式

### 3.1 時間格式

所有時間欄位為 **ISO 8601 UTC**，例如：

```text
2025-11-20T16:22:02
```

Flutter 端可以用 `DateTime.parse(...)` 解析。

### 3.2 錯誤格式（範例）

```json
{
  "detail": "not enough coins"
}
```

遇到 4xx / 5xx 時，從 `detail` 取錯誤訊息即可。

---

## 4. User Summary（首頁資料）

**GET** `/me`

> 需要帶 Authorization header。

- Response JSON（重點欄位）：

```json
{
  "user_id": 15,
  "status": "guest",
  "coins": 250,
  "today_checkin_status": "none",  // "none" / "started" / "verified" / "awarded"
  "last_login_at": "2025-11-21T03:20:10",
  "exp": 1200,
  "level": 8,
  "chicken_status": "normal",      // "weak" / "normal" / "strong"
  "weekly_activity_count": 3,
  "current_streak": 5
}
```

> Flutter 主畫面可以只打這一支 API，就拿到  
> - 金幣、等級、EXP  
> - 小雞狀態（虛弱/一般/強壯）  
> - 本週運動次數、連續運動天數  
> - 今天打卡狀態（顯示「已打卡 / 尚未打卡」）

---

## 5. 打卡系統（Checkins）

Base path：`/checkins`

### 5.1 開始打卡

**POST** `/checkins/start`

- Request JSON：

```json
{
  "lat": 25.033,
  "lng": 121.565
}
```

- Response JSON：

```json
{
  "checkin_id": 11,
  "status": "started",
  "started_at": "2025-11-20T16:22:02"
}
```

> Flutter：  
> - 進入健身房畫面 → 呼叫 `/checkins/start` → 記住 `checkin_id`。  
> - 之後心跳與結束都要帶同一個 `checkin_id`。

---

### 5.2 心跳（維持累積時間）

**POST** `/checkins/heartbeat`

- Request JSON：

```json
{
  "checkin_id": 11
}
```

- Response JSON：

```json
{
  "ok": true,
  "accum_minutes": 18
}
```

> 建議：前端每 1～3 分鐘呼叫一次即可。

---

### 5.3 結束打卡

**POST** `/checkins/end`

- Request JSON：

```json
{
  "checkin_id": 11,
  "lat": 25.0335,
  "lng": 121.5653
}
```

- Response JSON：

```json
{
  "verified": true,
  "dwell_minutes": 35,
  "coins_awarded": 60
}
```

> 若停留時間不足 30 分鐘，`verified=false` & `coins_awarded=0`。

---

### 5.4 歷史紀錄 / 最新打卡

- **GET** `/checkins/latest`  
- **GET** `/checkins/history?limit=50&offset=0`

回傳每筆打卡的狀態、開始/結束時間、拿到的金幣等。

---

## 6. 跑步系統（Runs）

Base path：`/runs`

### 6.1 上傳跑步總結

**POST** `/runs/summary`

- Request JSON：

```json
{
  "distance_km": 3.50,
  "duration_sec": 1800,
  "max_speed_kmh": 12.34
}
```

- Response JSON：

```json
{
  "coins_awarded": 120,
  "status": "awarded"      // or "rejected"（例如超速）
}
```

> 後端會依距離 × 25–50 金幣，並檢查 `max_speed_kmh` 是否 > 20。

### 6.2 歷史紀錄

**GET** `/runs/history?limit=50&offset=0`

---

## 7. 訓練紀錄（Trainings）

Base path：`/trainings`

### 7.1 新增訓練紀錄

**POST** `/trainings/logs`

- Request JSON：

```json
{
  "exercise_name": "Bench Press",
  "weight_kg": 40.0,
  "reps": 12,
  "sets": 3,
  "performed_at": null
}
```

`performed_at` 若為 `null` 或不填，後端會自動用現在時間。

- Response JSON（單筆紀錄）：

```json
{
  "id": 1,
  "exercise_name": "Bench Press",
  "weight_kg": 40.0,
  "reps": 12,
  "sets": 3,
  "volume": 1440,
  "performed_at": "2025-11-20T15:00:00"
}
```

---

### 7.2 訓練歷史

**GET** `/trainings/logs/history?limit=50&offset=0`

### 7.3 訓練統計圖用資料

**GET** `/trainings/stats?range=week`  
**GET** `/trainings/stats?range=month`

- Response JSON：

```json
{
  "range": "week",
  "points": [
    {
      "date": "2025-11-18",
      "total_volume": 3000,
      "total_sets": 12
    }
  ]
}
```

> Flutter 可以直接拿 `points` 畫折線圖 / 長條圖。

---

## 8. 商店與背包

### 8.1 商店商品列表

**GET** `/store/items`

- Response JSON：

```json
[
  {
    "id": 1,
    "name": "蛋白粉小罐",
    "price_coins": 100,
    "exp_min": 50,
    "exp_max": 80,
    "description": "給小雞補充一點蛋白質"
  }
]
```

---

### 8.2 購買商品

**POST** `/store/purchase`

- Request JSON：

```json
{
  "item_id": 1
}
```

- Response JSON：

```json
{
  "item_id": 1,
  "item_name": "蛋白粉小罐",
  "coins_spent": 100,
  "coins_after": 250
}
```

> 若金幣不足 → 會回傳 400 + `{ "detail": "not enough coins" }`。

---

## 9. 背包與使用道具

Base path：`/inventory`

### 9.1 查看背包

**GET** `/inventory/bag`

- Response JSON：

```json
[
  {
    "item_id": 1,
    "name": "蛋白粉小罐",
    "quantity": 3,
    "description": "給小雞補充一點蛋白質"
  }
]
```

---

### 9.2 使用道具

**POST** `/inventory/use`

- Request JSON：

```json
{
  "item_id": 1
}
```

- Response JSON：

```json
{
  "item_id": 1,
  "item_name": "蛋白粉小罐",
  "exp_gain": 90,
  "new_exp": 1300,
  "new_level": 9,
  "remaining_quantity": 2
}
```

> EXP 會根據小雞狀態倍率（虛弱 0.5 / 一般 1.0 / 強壯 1.5）自動計算，並可能解鎖成就。

---

## 10. 成就與每週挑戰

### 10.1 成就列表（包含是否已解鎖）

**GET** `/achievements/my`

- Response JSON：

```json
[
  {
    "id": 1,
    "code": "FIRST_CHECKIN",
    "name": "第一次打卡",
    "description": "完成第一次打卡",
    "unlocked": true,
    "unlocked_at": "2025-11-20T15:30:00"
  }
]
```

---

### 10.2 本週挑戰狀態

**GET** `/challenges/weekly`

- Response JSON：

```json
{
  "week_start": "2025-11-17T00:00:00",
  "target_count": 3,
  "current_count": 2,
  "reward_coins": 50,
  "reward_exp": 100,
  "completed_at": null
}
```

> Flutter 可以用這個畫「本週目標：運動 3 次」，並顯示目前進度條。

---

## 11. Flutter 串接範例（簡化版）

以 `http` 套件為例：

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

const baseUrl = 'http://127.0.0.1:8000';

Future<Map<String, dynamic>> guestLogin() async {
  final resp = await http.post(
    Uri.parse('$baseUrl/auth/guest'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'platform': 'android',
      'app_version': '1.0.0',
      'device_id': null,
    }),
  );

  if (resp.statusCode == 200) {
    return jsonDecode(resp.body);
  } else {
    throw Exception('Guest login failed: ${resp.body}');
  }
}

Future<Map<String, dynamic>> fetchMe(String accessToken) async {
  final resp = await http.get(
    Uri.parse('$baseUrl/me'),
    headers: {
      'Authorization': 'Bearer $accessToken',
    },
  );

  if (resp.statusCode == 200) {
    return jsonDecode(resp.body);
  } else {
    throw Exception('Fetch /me failed: ${resp.body}');
  }
}
```

---

以上就是給前端使用的 **精簡版 README**。  
需要更完整的資料表說明或錯誤碼列表，可以再另外寫一份「進階版 README」。