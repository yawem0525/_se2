use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use rust_testing_app::{create_app, AppState, Task};
use tower::ServiceExt; // for app.oneshot()

#[tokio::test]
async fn test_api_create_and_get_tasks() {
    let app = create_app(AppState::default());

    // 1. POST /api/tasks (新增資料)
    let payload = serde_json::json!({ "title": "系統測試任務" });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/tasks")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_vec(&payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let created_task: Task = serde_json::from_slice(&body).unwrap();
    assert_eq!(created_task.title, "系統測試任務");

    // 2. GET /api/tasks (取得資料並驗證)
    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/api/tasks")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let tasks: Vec<Task> = serde_json::from_slice(&body).unwrap();
    assert_eq!(tasks.len(), 1);
    assert_eq!(tasks[0].title, "系統測試任務");
}

#[tokio::test]
async fn test_api_create_task_validation_failure() {
    let app = create_app(AppState::default());

    // 送出空標題測試 400 Bad Request
    let payload = serde_json::json!({ "title": "   " });
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/tasks")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_vec(&payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}
