# 我獨自生肌 Backend API 說明 (for Flutter Integration)

本文件給前端 Flutter 使用，說明目前已完成的後端 API 以及整合方式。  
後端技術：**FastAPI + MySQL**，提供 JWT 驗證、打卡 / 跑步 / 課表紀錄、商店與養成、成就與挑戰等功能。

---

## 1. 基本資訊

- Base URL（開發機）：
  - `http://127.0.0.1:8000`
- 所有需要登入的 API **都要帶 JWT Access Token**：
  - HTTP Header：`Authorization: Bearer <access_token>`

---

## 2. 身分驗證流程

### 2.1 遊客登入 `POST /auth/guest`

**Request body**

```json
{
  "platform": "android",
  "app_version": "1.0.0",
  "device_id": "optional-device-id-or-null"
}
```

- `platform`: 目前支援 `"android" | "ios" | "web"`（後端沒強制，但請照這三種傳）
- `device_id`: 前端第一次可以不傳（或 `null`），之後建議自己生成 / 存在 local，再帶上。

**Response**

```json
{
  "user_id": 15,
  "access_token": "<JWT>",
  "expires_in": 1199,
  "is_guest": true,
  "refresh_token": "<REFRESH_TOKEN>",
  "refresh_expires_in": 1814399
}
```

- `access_token`: 後續所有需要登入的 API 都要帶在 Header。
- `expires_in`: Access Token 有效秒數。
- `refresh_token`: 用來換新 Access Token。請安全地存起來（例如 secure storage）。

> **前端建議：**
> - App 啟動時：
>   1. 若本地有 `refresh_token` → 試著呼叫 `/refresh` 換新 AT。
>   2. 若沒有 → 呼叫 `/auth/guest` 取得新的 AT / RT。

---

### 2.2 換 Access Token `POST /refresh`

**Request body**

```json
{
  "refresh_token": "<REFRESH_TOKEN>"
}
```

**Response**

```json
{
  "access_token": "<NEW_JWT>",
  "expires_in": 1200
}
```

- 若 RT 失效或被撤銷，會回傳 `401`。

---

## 3. 使用者首頁資訊 `/me`

### 3.1 取得我的總覽 `GET /me`

**Header**

```http
Authorization: Bearer <access_token>
```

**Response 範例**

```json
{
  "user_id": 15,
  "status": "guest",
  "coins": 230,
  "today_checkin_status": "awarded",
  "last_login_at": "2025-11-20T16:22:02",
  "exp": 1234,
  "level": 8,
  "chicken_status": "strong",
  "weekly_activity_count": 5,
  "current_streak": 3
}
```

欄位說明：

- `coins`: 目前金幣餘額（從 `coins_ledger` 加總）。
- `today_checkin_status`:
  - `"none"`：今天尚未打卡
  - `"started" | "verified" | "awarded"`：今天有打卡，狀態如名。
- `exp`, `level`: 小雞養成等級與總經驗值（依 EXP 對照表計算）。
- `chicken_status`: `"weak" | "normal" | "strong"`，依本週運動次數決定，會影響之後吃道具 / 打卡 / 跑步給的 EXP 倍率。
- `weekly_activity_count`: 本週運動總次數（打卡成功 + 跑步有發獎勵）。
- `current_streak`: 連續運動天數（今天 + 往前連續有運動的天數）。

> **前端建議：**  
> - Home 頁一進來先打 `/me`，決定：
>   - 顯示小雞目前等級 / 狀態圖示  
>   - 顯示金幣、連續打卡天數、這週已運動幾次  
>   - 今天是否已打卡（決定是否顯示「開始打卡」BTN）

---

## 4. 打卡系統 `/checkins`

打卡流程：  
1. `POST /checkins/start` → 拿到 `checkin_id`  
2. 過程中定期 `POST /checkins/heartbeat`（例如每 1–2 分鐘呼叫一次）  
3. 離開健身房時 `POST /checkins/end` → 回傳實際停留分鐘 + 獲得金幣  

> 後端會依累積停留分鐘數、每天上限等條件決定是否給幣與多少幣。

---

### 4.1 開始打卡 `POST /checkins/start`

**Request**

```json
{
  "lat": 25.033,
  "lng": 121.565
}
```

**Response**

```json
{
  "checkin_id": 11,
  "status": "started",
  "started_at": "2025-11-20T16:22:02"
}
```

- 前端只需要記住 `checkin_id` 即可。

---

### 4.2 心跳（累積時間）`POST /checkins/heartbeat`

**Request**

```json
{
  "checkin_id": 11
}
```

**Response**

```json
{
  "ok": true,
  "accum_minutes": 23
}
```

- 後端會自動計算距離上次 heartbeat 發送隔了幾分鐘，把累計時間記起來。

---

### 4.3 結束打卡 `POST /checkins/end`

**Request**

```json
{
  "checkin_id": 11,
  "lat": 25.033,
  "lng": 121.565
}
```

**Response**

```json
{
  "verified": true,
  "dwell_minutes": 42,
  "coins_awarded": 120
}
```

- 若停留時間 `< 30` 分鐘 → `verified=false`, `coins_awarded=0`。  
- 每天有獎勵的打卡次數有限制（目前最多兩次）。  
- 若這次有發幣，後端會：
  - 寫入 `coins_ledger`
  - 給小雞 EXP（含「狀態倍率」）
  - 檢查週挑戰與成就是否達成。  

---

### 4.4 其他打卡查詢 API

- `GET /checkins/latest`：拿到最近一筆打卡記錄。  
- `GET /checkins/history?limit=50&offset=0`：打卡歷史列表。  

回傳格式為：

```json
{
  "id": 11,
  "status": "awarded",
  "dwell_minutes": 42,
  "coins_awarded": 120,
  "reason": null,
  "started_at": "2025-11-20T16:22:02",
  "ended_at": "2025-11-20T17:04:02"
}
```

---

## 5. 跑步紀錄 `/runs`

### 5.1 上傳一次跑步結果 `POST /runs/summary`

**Request**

```json
{
  "distance_km": 3.500,
  "duration_sec": 1800,
  "max_speed_kmh": 12.34
}
```

- `max_speed_kmh > 20` 會被視為作弊，這筆跑步會直接 `rejected` 並不給金幣。

**Response**

```json
{
  "coins_awarded": 120,
  "status": "awarded"
}
```

- 會依距離隨機給金幣（每 km 25 ~ 50 金幣）。  
- 若有發幣，後端會：
  - 寫 `coins_ledger`
  - 給 EXP（含狀態倍率）
  - 檢查週挑戰與成就。  

### 5.2 歷史紀錄 `GET /runs/history?limit=50&offset=0`

回傳陣列，每筆格式：

```json
{
  "id": 1,
  "distance_km": 3.5,
  "duration_sec": 1800,
  "max_speed_kmh": 12.34,
  "coins_awarded": 120,
  "status": "awarded",
  "reason": null,
  "created_at": "2025-11-20T16:22:02"
}
```

---

## 6. 商店與背包 `/store`, `/inventory`

### 6.1 商品列表 `GET /store/items`

**Response**

```json
[
  {
    "id": 1,
    "name": "蛋白粉",
    "price_coins": 100,
    "exp_min": 50,
    "exp_max": 80,
    "description": "小雞最愛的蛋白粉"
  }
]
```

- `exp_min`～`exp_max`：吃下去時後端會隨機選一個作為基礎 EXP，再乘以「狀態倍率」。

### 6.2 購買道具 `POST /store/purchase`

**Request**

```json
{
  "item_id": 1
}
```

**Response**

```json
{
  "item_id": 1,
  "item_name": "蛋白粉",
  "coins_spent": 100,
  "coins_after": 130
}
```

- 若金幣不足會回 `400` + `{"detail": "not enough coins"}`。  

---

### 6.3 查看背包 `GET /inventory/bag`

**Response**

```json
[
  {
    "item_id": 1,
    "name": "蛋白粉",
    "quantity": 3,
    "description": "小雞最愛的蛋白粉"
  }
]
```

---

### 6.4 使用道具 `POST /inventory/use`

**Request**

```json
{
  "item_id": 1
}
```

**Response**

```json
{
  "item_id": 1,
  "item_name": "蛋白粉",
  "exp_gain": 75,
  "new_exp": 1309,
  "new_level": 9,
  "remaining_quantity": 2
}
```

- `exp_gain`: 已經乘過「狀態倍率」後的最終 EXP。  
- `remaining_quantity`: 用完之後背包剩餘數量。  

後端流程：  
1. 檢查背包是否有該道具  
2. 根據 `exp_min ~ exp_max` 算出基礎 EXP  
3. 查本週運動次數 → 小雞狀態 → 倍率 → 算出實際 EXP  
4. 更新 user EXP / Level  
5. 檢查是否解鎖成就。  

---

## 7. 訓練課表與統計 `/trainings`

### 7.1 新增訓練紀錄 `POST /trainings/logs`

**Request**

```json
{
  "exercise_name": "Bench Press",
  "weight_kg": 40.0,
  "reps": 12,
  "sets": 3,
  "performed_at": "2025-11-20T16:22:02"
}
```

- `performed_at` 可不填，後端會用現在時間。

**Response**

```json
{
  "id": 1,
  "exercise_name": "Bench Press",
  "weight_kg": 40.0,
  "reps": 12,
  "sets": 3,
  "volume": 1440,
  "performed_at": "2025-11-20T16:22:02"
}
```

- `volume = weight * reps * sets`（後端計算完回傳）。

---

### 7.2 歷史訓練紀錄 `GET /trainings/logs/history?limit=50&offset=0`

回傳陣列，每筆格式同上。  

---

### 7.3 訓練統計圖用 `GET /trainings/stats?range=week|month`

**Response 範例**

```json
{
  "range": "week",
  "points": [
    {
      "date": "2025-11-18",
      "total_volume": 3000,
      "total_sets": 9
    },
    {
      "date": "2025-11-19",
      "total_volume": 1500,
      "total_sets": 3
    }
  ]
}
```

- `range = "week"`：最近 7 天  
- `range = "month"`：最近 30 天  
- 每天 group by `date`，合計該日總 volume / 總 sets。  

> **前端建議：**  
> - 可以拿 `points` 去畫折線圖 / 長條圖。

---

## 8. 成就與每週挑戰

### 8.1 我的成就列表 `GET /achievements/my`

**Response 範例**

```json
[
  {
    "id": 1,
    "code": "FIRST_CHECKIN",
    "name": "第一次打卡",
    "description": "完成第一次健身房打卡",
    "unlocked": true,
    "unlocked_at": "2025-11-20T16:22:02"
  }
]
```

- `unlocked = true` 表示已解鎖。  

> 成就是在：
> - 打卡成功
> - 跑步成功
> - 吃道具升級  
> 時由後端自動檢查並解鎖。  

---

### 8.2 本週挑戰狀態 `GET /challenges/weekly`

**Response 範例**

```json
{
  "week_start": "2025-11-17T00:00:00",
  "target_count": 3,
  "current_count": 4,
  "reward_coins": 50,
  "reward_exp": 100,
  "completed_at": "2025-11-20T16:22:02"
}
```

- `week_start`: 本週一 00:00（UTC）  
- `target_count`: 本週目標運動次數（目前預設 3 次）  
- `current_count`: 目前已完成次數（打卡 + 跑步的有效次數）。  
- `completed_at`: 若非 `null` 表示已完成並領取獎勵（coins + exp）。  

> 後端會在打卡成功 / 跑步成功時自動檢查是否達成挑戰並發獎勵。前端只要定期呼叫這個 API 來顯示 UI 即可。

---

## 9. Flutter 串接建議流程（簡版）

1. **App 啟動**
   - 若本地有 `refresh_token` → `POST /refresh`  
   - 沒有 / 失敗 → `POST /auth/guest`，存 `access_token` + `refresh_token`

2. **每次呼叫 API**
   - Header 加上 `Authorization: Bearer <access_token>`  
   - 若收到 `401` → 嘗試 `POST /refresh`，成功後重新發送原本的 API

3. **Home 畫面**
   - `GET /me` → 更新：
     - 小雞狀態（exp / level / chicken_status）
     - 金幣
     - 本週運動次數與 streak
     - 今日打卡狀態

4. **健身房打卡流程**
   - 開始：`POST /checkins/start`
   - 計時：定期 `POST /checkins/heartbeat`
   - 結束：`POST /checkins/end` → 顯示獲得金幣 / EXP 動畫
   - Home 重打 `/me` 更新 UI

5. **跑步紀錄**
   - 跑完一次後，將距離 / 時間 / 最大速度丟給 `POST /runs/summary`
   - 成功的話再重打 `/me` 與 `/challenges/weekly` 更新 UI。

6. **商店 & 道具**
   - 商店頁：`GET /store/items`
   - 購買：`POST /store/purchase`
   - 背包頁：`GET /inventory/bag`
   - 使用道具：`POST /inventory/use` → 之後重打 `/me`

7. **訓練 & 成就**
   - 新增訓練：`POST /trainings/logs`
   - 歷史紀錄 & 統計圖：`GET /trainings/logs/history`、`GET /trainings/stats`
   - 成就頁：`GET /achievements/my`
   - 每週挑戰頁：`GET /challenges/weekly`
