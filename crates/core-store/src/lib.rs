use serde::{de::DeserializeOwned, Serialize};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StoreError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

pub fn portable_data_dir() -> Result<PathBuf, StoreError> {
    Ok(std::env::current_dir()?.join("data"))
}

pub fn init_portable_layout() -> Result<PathBuf, StoreError> {
    let data_dir = portable_data_dir()?;
    fs::create_dir_all(data_dir.join("logs"))?;

    let settings_path = data_dir.join("settings.json");
    if !settings_path.exists() {
        fs::write(&settings_path, "{}")?;
    }

    Ok(data_dir)
}

pub fn save_json<T: Serialize>(relative_path: &str, value: &T) -> Result<(), StoreError> {
    let path = portable_data_dir()?.join(relative_path);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    fs::write(path, serde_json::to_vec_pretty(value)?)?;
    Ok(())
}

pub fn load_json<T: DeserializeOwned>(relative_path: &str) -> Result<T, StoreError> {
    let path = portable_data_dir()?.join(relative_path);
    let content = fs::read(path)?;
    Ok(serde_json::from_slice(&content)?)
}

/// Append a timestamped log line to `data/logs/app.log`.
pub fn append_log(message: &str) -> Result<(), StoreError> {
    let log_path = portable_data_dir()?.join("logs").join("app.log");
    if let Some(parent) = log_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f");
    let mut file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)?;
    writeln!(file, "[{now}] {message}")?;
    Ok(())
}
