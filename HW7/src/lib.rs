use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use tower_http::services::ServeDir;

// --- 領域模型與業務邏輯 ---
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Task {
    pub id: u64,
    pub title: String,
    pub completed: bool,
}

#[derive(Debug, Deserialize)]
pub struct CreateTaskPayload {
    pub title: String,
}

#[derive(Clone, Default)]
pub struct AppState {
    pub tasks: Arc<Mutex<Vec<Task>>>,
    pub next_id: Arc<Mutex<u64>>,
}

/// 核心業務邏輯驗證函式（單元測試目標）
pub fn validate_task_title(title: &str) -> Result<String, &'static str> {
    let trimmed = title.trim();
    if trimmed.is_empty() {
        return Err("標題不能為空");
    }
    if trimmed.len() > 50 {
        return Err("標題長度不能超過 50 個字元");
    }
    Ok(trimmed.to_string())
}

// --- HTTP Handlers ---
pub async fn get_tasks(State(state): State<AppState>) -> Json<Vec<Task>> {
    let tasks = state.tasks.lock().unwrap().clone();
    Json(tasks)
}

pub async fn create_task(
    State(state): State<AppState>,
    Json(payload): Json<CreateTaskPayload>,
) -> Result<(StatusCode, Json<Task>), (StatusCode, String)> {
    let validated_title = validate_task_title(&payload.title)
        .map_err(|err| (StatusCode.BAD_REQUEST, err.to_string()))?;

    let mut next_id = state.next_id.lock().unwrap();
    let task = Task {
        id: *next_id,
        title: validated_title,
        completed: false,
    };
    *next_id += 1;

    state.tasks.lock().unwrap().push(task.clone());
    Ok((StatusCode::CREATED, Json(task)))
}

pub async fn delete_task(
    State(state): State<AppState>,
    Path(id): Path<u64>,
) -> impl IntoResponse {
    let mut tasks = state.tasks.lock().unwrap();
    let initial_len = tasks.len();
    tasks.retain(|t| t.id != id);

    if tasks.len() < initial_len {
        StatusCode::NO_CONTENT
    } else {
        StatusCode::NOT_FOUND
    }
}

// --- 建立 App Router ---
pub fn create_app(state: AppState) -> Router {
    Router::new()
        .route("/api/tasks", get(get_tasks).post(create_task))
        .route("/api/tasks/:id", delete(delete_task))
        .fallback_service(ServeDir::new("static"))
        .with_state(state)
}

// ==========================================
// 1. 單元測試 (Unit Tests)
// ==========================================
#[cfg(test)]
mod unit_tests {
    use super::*;

    #[test]
    fn test_validate_task_title_valid() {
        let result = validate_task_title("撰寫軟體工程報告");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "撰寫軟體工程報告");
    }

    #[test]
    fn test_validate_task_title_trim_whitespace() {
        let result = validate_task_title("   學習 Rust   ");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "學習 Rust");
    }

    #[test]
    fn test_validate_task_title_empty_fails() {
        let result = validate_task_title("    ");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "標題不能為空");
    }

    #[test]
    fn test_validate_task_title_too_long_fails() {
        let long_title = "a".repeat(51);
        let result = validate_task_title(&long_title);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "標題長度不能超過 50 個字元");
    }
}
