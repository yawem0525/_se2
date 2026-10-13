# mycurl.py 使用範例

這個 Python 腳本的行為邏輯與原生的 `curl` 非常相似。以下是幾個常見的操作範例：

## 1. 基本 GET 請求

僅獲取目標網址的回應內容（例如 HTML 原始碼）：

```bash
python mycurl.py http://example.com
```

## 2. 顯示 HTTP 回應標頭 (`-i`)

除了回應內容外，在最上方同時印出 HTTP 狀態碼與所有回應標頭（類似 `curl -i`）：

```bash
python mycurl.py -i http://example.com
```

## 3. 發送 POST 請求並附帶資料與自訂標頭

發送一個帶有 JSON 資料實體，並且包含多個自訂標頭（如 `Content-Type` 和 `Authorization`）的 POST 請求：

```bash
python mycurl.py -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-token" \
  -d '{"name": "test", "value": 123}' \
  https://httpbin.org/post
```
