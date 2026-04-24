use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use std::thread;

use tauri::{
    AppHandle, Emitter, Manager, Runtime,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};
use tauri_plugin_clipboard_manager::ClipboardExt;
use enigo::{Enigo, Key, Keyboard, Settings};

struct BackendProcess(Mutex<Option<Child>>);

// ── 粘贴文字到当前光标位置 ───────────────────────────────────────────────────
#[tauri::command]
fn paste_text(app: AppHandle, text: String) -> Result<(), String> {
    app.clipboard()
        .write_text(text)
        .map_err(|e| e.to_string())?;

    thread::sleep(Duration::from_millis(100));

    let mut enigo = Enigo::new(&Settings::default()).map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    {
        enigo.key(Key::Meta, enigo::Direction::Press).ok();
        enigo.key(Key::Unicode('v'), enigo::Direction::Click).ok();
        enigo.key(Key::Meta, enigo::Direction::Release).ok();
    }
    #[cfg(not(target_os = "macos"))]
    {
        enigo.key(Key::Control, enigo::Direction::Press).ok();
        enigo.key(Key::Unicode('v'), enigo::Direction::Click).ok();
        enigo.key(Key::Control, enigo::Direction::Release).ok();
    }

    Ok(())
}

// ── Tauri 入口 ────────────────────────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // ── 启动 Python backend ──────────────────────────────────────
            let script = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .join("backend")
                .join("main.py");

            let child = Command::new("python3").arg(&script).spawn().ok();
            *app.state::<BackendProcess>().0.lock().unwrap() = child;

            // ── 系统托盘 ────────────────────────────────────────────────
            let stats_item  = MenuItem::with_id(app, "stats",  "📊 学习进展", true, None::<&str>)?;
            let review_item = MenuItem::with_id(app, "review", "🔁 开始复习", true, None::<&str>)?;
            let quit_item   = MenuItem::with_id(app, "quit",   "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&stats_item, &review_item, &quit_item])?;

            TrayIconBuilder::new()
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "stats"  => { let _ = show_or_create(app, "stats"); }
                    "review" => { let _ = show_or_create(app, "review"); }
                    "quit"   => {
                        if let Ok(mut g) = app.state::<BackendProcess>().0.lock() {
                            if let Some(mut c) = g.take() { let _ = c.kill(); }
                        }
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up, ..
                    } = event {
                        let _ = show_or_create(tray.app_handle(), "input");
                    }
                })
                .build(app)?;

            // ── 快捷键：Cmd+Option+I / Ctrl+Alt+I → 输入框 ──────────────
            let h1 = app.handle().clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(Some(Modifiers::ALT | Modifiers::SUPER), Code::KeyI),
                move |_, _, _| { let _ = show_or_create(&h1, "input"); },
            )?;

            // ── 快捷键：Cmd+Option+T / Ctrl+Alt+T → 划词翻译 ────────────
            let h2 = app.handle().clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(Some(Modifiers::ALT | Modifiers::SUPER), Code::KeyT),
                move |app, _, _| {
                    // 模拟 Cmd+C 复制选中文字
                    if let Ok(mut enigo) = Enigo::new(&Settings::default()) {
                        #[cfg(target_os = "macos")]
                        {
                            enigo.key(Key::Meta, enigo::Direction::Press).ok();
                            enigo.key(Key::Unicode('c'), enigo::Direction::Click).ok();
                            enigo.key(Key::Meta, enigo::Direction::Release).ok();
                        }
                        #[cfg(not(target_os = "macos"))]
                        {
                            enigo.key(Key::Control, enigo::Direction::Press).ok();
                            enigo.key(Key::Unicode('c'), enigo::Direction::Click).ok();
                            enigo.key(Key::Control, enigo::Direction::Release).ok();
                        }
                    }
                    thread::sleep(Duration::from_millis(200));

                    if let Ok(text) = app.clipboard().read_text() {
                        let text = text.trim().to_string();
                        if !text.is_empty() {
                            let _ = h2.emit("translate-selected", &text);
                            let _ = show_or_create(&h2, "translate");
                        }
                    }
                },
            )?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![paste_text])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn show_or_create<R: Runtime>(app: &AppHandle<R>, label: &str) -> tauri::Result<()> {
    if let Some(w) = app.get_webview_window(label) {
        w.show()?;
        w.set_focus()?;
    }
    Ok(())
}
