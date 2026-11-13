/// Cloudflare Workers 應用程式客戶端設定
pub struct CloudflareAppClient {
    pub base_url: String,
}

impl CloudflareAppClient {
    /// 建立新的客戶端實例
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into().trim_end_matches('/').to_string(),
        }
    }

    /// 組合完整的 API 端點路徑
    pub fn endpoint(&self, path: &str) -> String {
        let clean_path = path.trim_start_matches('/');
        format!("{}/{}", self.base_url, clean_path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_clean_url() {
        let client = CloudflareAppClient::new("https://example.workers.dev/");
        assert_eq!(client.endpoint("/api/v1"), "https://example.workers.dev/api/v1");
    }
}
