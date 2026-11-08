use rust_testing_app::{create_app, AppState};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let state = AppState::default();
    let app = create_app(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    println!("伺服器已啟動：http://localhost:3000");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
