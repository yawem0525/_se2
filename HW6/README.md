# Docker 微服務系統建置與學習記錄 (Microservices with Docker)

本專案使用 Docker 與 Docker Compose 建立一套現代化三層微服務架構，包含 **Nginx** 反向代理、**Python FastAPI** 後端 API 與 **PostgreSQL 16** 資料庫，並整合 Web 儀表板供即時狀態驗證。

---

## 1. Docker 核心概念與學習筆記

### 1.1 什麼是 Docker？
Docker 是一種開源的容器化（Containerization）技術，利用 Linux Kernel 的核心功能（如 Namespaces 資源隔離、cgroups 資源配額限額）將應用程式及其所有執行環境、函式庫打包在一個輕量、獨立的虛擬環境中。

### 1.2 核心元件與術語
| 元件 | 說明 |
| :--- | :--- |
| **Image (映像檔)** | 唯讀模板，包含執行應用程式所需的程式碼、執行庫、環境變數與設定檔。 |
| **Container (容器)** | 映像檔的執行實體。容器之間預設彼此隔離，啟動快速且消耗資源極少。 |
| **Dockerfile** | 純文字構建腳本，記載建立特定映像檔的一連串指令（如 `FROM`、`COPY`、`RUN`、`CMD`）。 |
| **Docker Compose** | 多容器協調管理工具，透過 `docker-compose.yml` 統一編排服務、網路及資料磁碟。 |
| **Volume (資料卷)** | 用於將容器內部目錄掛載至宿主機，確保容器刪除後資料仍可持久化保存。 |
| **Network (網路)** | 建立虛擬橋接網路（Bridge Network），讓同一網路內的容器透過服務名稱（DNS）互相解析通訊。 |

### 1.3 常用 Docker 命令速查表
```bash
# 映像檔操作
docker build -t <image_name>:<tag> .   # 根據 Dockerfile 構建映像檔
docker images                          # 查看本機所有映像檔
docker rmi <image_id>                  # 刪除指定映像檔

# 容器生命週期操作
docker run -d -p 8080:80 --name web nginx  # 背景啟動容器並映射 Port
docker ps                                  # 查看目前執行中的容器 (-a 查看所有)
docker stop <container_id>                 # 停止容器
docker start <container_id>                # 啟動容器
docker rm <container_id>                   # 刪除容器 (-f 強制刪除)

# 除錯與維護
docker logs -f <container_name>            # 即時追蹤容器輸出日誌
docker exec -it <container_name> sh        # 進入容器終端機
docker inspect <container_name>            # 檢查容器詳細設定與 IP

# Docker Compose 操作
docker compose up -d --build               # 構建並於背景啟動所有微服務
docker compose ps                          # 檢查 Compose 管理的服務狀態
docker compose logs -f <service_name>      # 檢視特定服務的日誌
docker compose down                        # 停止並移除所有容器與虛擬網路
docker compose down -v                     # 停止容器並連同 Volume 資料卷一併刪除
