import argparse
import urllib.request
import urllib.error
import sys

def main():
    # 設定命令列參數解析
    parser = argparse.ArgumentParser(description="輕量版類似 curl 的 HTTP 請求工具")
    parser.add_argument("url", help="目標 URL")
    parser.add_argument("-X", "--request", default="GET", help="HTTP 方法 (例如 GET, POST, PUT, DELETE)")
    parser.add_argument("-d", "--data", help="傳送的資料內容 (預設會將方法轉為 POST)")
    parser.add_argument("-H", "--header", action="append", help="自訂標頭 (可多次使用，例如 'Content-Type: application/json')")
    parser.add_argument("-i", "--include", action="store_true", help="在輸出中包含 HTTP 回應標頭")

    args = parser.parse_args()

    # 處理自訂標頭
    headers = {}
    if args.header:
        for h in args.header:
            parts = h.split(":", 1)
            if len(parts) == 2:
                headers[parts[0].strip()] = parts[1].strip()

    # 處理傳送資料
    data = None
    if args.data:
        data = args.data.encode('utf-8')
        # 仿照 curl 行為：如果有提供 -d，且未強制指定方法，預設轉為 POST
        if args.request == "GET" and "-X" not in sys.argv and "--request" not in sys.argv:
            args.request = "POST"

    # 建立 HTTP 請求
    req = urllib.request.Request(args.url, data=data, headers=headers, method=args.request)

    try:
        # 發送請求並接收回應
        with urllib.request.urlopen(req) as response:
            body = response.read().decode('utf-8', errors='replace')
            
            # 若有 -i 參數，印出回應標頭
            if args.include:
                print(f"HTTP/1.1 {response.status} {response.reason}")
                for k, v in response.headers.items():
                    print(f"{k}: {v}")
                print() # 標頭與內文之間的空行
            
            # 印出回應內文
            print(body)
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        if args.include:
            for k, v in e.headers.items():
                print(f"{k}: {v}")
            print()
        print(e.read().decode('utf-8', errors='replace'))
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"未預期的錯誤: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
