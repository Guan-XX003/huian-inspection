use std::{
    fs::{self, OpenOptions},
    net::TcpStream,
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    time::Duration,
};

use tauri::{Manager, RunEvent};

fn api_is_ready() -> bool {
    TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().expect("valid local API address"),
        Duration::from_millis(250),
    )
    .is_ok()
}

fn api_sidecar_path(app: &tauri::App) -> Option<PathBuf> {
    let resource_dir = app.path().resource_dir().ok()?;
    let executable_name = if cfg!(windows) {
        "huian-api.exe"
    } else {
        "huian-api"
    };
    let candidates = [
        resource_dir.join("huian-api").join(executable_name),
        resource_dir
            .join("_up_")
            .join("_up_")
            .join("api")
            .join("dist")
            .join("huian-api")
            .join(executable_name),
    ];
    candidates
        .into_iter()
        .find(|candidate| candidate.exists())
}

fn start_api_sidecar(app: &tauri::App) -> Result<Option<Child>, Box<dyn std::error::Error>> {
    if api_is_ready() {
        return Ok(None);
    }
    let Some(sidecar) = api_sidecar_path(app) else {
        eprintln!("No bundled API sidecar found; desktop will rely on an existing local API service.");
        return Ok(None);
    };
    let sidecar_dir = sidecar.parent().map(PathBuf::from);
    let log_file = api_log_file();
    let stdout = log_file
        .as_ref()
        .and_then(|file| file.try_clone().ok())
        .map(Stdio::from)
        .unwrap_or_else(Stdio::null);
    let stderr = log_file
        .map(Stdio::from)
        .unwrap_or_else(Stdio::null);
    let mut command = Command::new(sidecar);
    if let Some(sidecar_dir) = sidecar_dir {
        command.current_dir(sidecar_dir);
    }
    let child = command
        .env("HUIAN_DESKTOP", "1")
        .env("HUIAN_API_HOST", "127.0.0.1")
        .env("HUIAN_API_PORT", "8000")
        .stdin(Stdio::null())
        .stdout(stdout)
        .stderr(stderr)
        .spawn()?;
    Ok(Some(child))
}

fn api_log_file() -> Option<std::fs::File> {
    let base_dir = if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME")
            .map(PathBuf::from)
            .map(|home| home.join("Library").join("Application Support"))
    } else {
        std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".local").join("share")))
    }?;
    let log_dir = base_dir.join("HuianInspectionAI").join("logs");
    fs::create_dir_all(&log_dir).ok()?;
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_dir.join("huian-api.log"))
        .ok()
}

fn stop_api_sidecar(api_process: &Arc<Mutex<Option<Child>>>) {
    if let Ok(mut guard) = api_process.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn main() {
    let api_process: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let setup_api_process = Arc::clone(&api_process);
    let run_api_process = Arc::clone(&api_process);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            let child = start_api_sidecar(app).map_err(|error| error.to_string())?;
            if let Some(child) = child {
                if let Ok(mut guard) = setup_api_process.lock() {
                    *guard = Some(child);
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| match event {
            RunEvent::ExitRequested { .. } | RunEvent::Exit => stop_api_sidecar(&run_api_process),
            _ => {}
        });
}
