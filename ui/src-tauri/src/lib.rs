use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use std::thread;
use std::io::Write;

use tauri::{
    AppHandle, Manager, Runtime, WebviewUrl, WebviewWindow,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    webview::WebviewWindowBuilder,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Shortcut};
#[cfg(not(target_os = "macos"))]
use enigo::{Enigo, Key, Keyboard, Settings};

struct BackendProcess(Mutex<Option<Child>>);
struct PreviousApp(Mutex<(String, i32)>);
struct PendingTranslate(Mutex<String>);

fn debug_log(message: impl AsRef<str>) {
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or_default();
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("/tmp/ai-input-tauri.log")
    {
        let _ = writeln!(f, "{ts} {}", message.as_ref());
    }
}

fn show_popup_window<R: Runtime>(w: &WebviewWindow<R>, label: &str) -> tauri::Result<()> {
    let all_spaces = w.set_visible_on_all_workspaces(true).is_ok();
    let always_top = w.set_always_on_top(true).is_ok();
    let _ = w.unminimize();
    w.show()?;
    w.set_focus()?;
    debug_log(format!("show_window label={label} all_spaces={all_spaces} always_top={always_top}"));
    Ok(())
}

// ── macOS CoreGraphics：直接把事件投递到目标进程，完全绕过输入法 ──────────────
#[cfg(target_os = "macos")]
mod cg {
    use std::ffi::c_void;
    use std::thread;
    use std::time::Duration;

    #[link(name = "CoreGraphics", kind = "framework")]
    extern "C" {
        fn CGEventSourceCreate(state_id: i32) -> *mut c_void;
        fn CGEventCreateKeyboardEvent(source: *mut c_void, virtual_key: u16, key_down: bool) -> *mut c_void;
        fn CGEventSetFlags(event: *mut c_void, flags: u64);
        fn CGEventPostToPid(pid: i32, event: *mut c_void);
        fn CFRelease(cf: *mut c_void);
    }

    const COMBINED_SESSION: i32 = 1;
    const CMD_FLAG: u64 = 0x0000_0100; // kCGEventFlagMaskCommand

    unsafe fn make_key(src: *mut c_void, keycode: u16, down: bool, flags: u64) -> *mut c_void {
        let ev = CGEventCreateKeyboardEvent(src, keycode, down);
        CGEventSetFlags(ev, flags);
        ev
    }

    // Cmd+V 直接投递到指定 PID（输入法看不到，不会触发 V 模式）
    pub fn cmd_v(pid: i32) {
        unsafe {
            let src = CGEventSourceCreate(COMBINED_SESSION);
            let cmd_dn = make_key(src, 55, true,  CMD_FLAG); // left Command down
            let v_dn   = make_key(src,  9, true,  CMD_FLAG); // V down  (keycode 9)
            let v_up   = make_key(src,  9, false, CMD_FLAG); // V up
            let cmd_up = make_key(src, 55, false, 0);        // Command up

            CGEventPostToPid(pid, cmd_dn);
            thread::sleep(Duration::from_millis(20));
            CGEventPostToPid(pid, v_dn);
            thread::sleep(Duration::from_millis(20));
            CGEventPostToPid(pid, v_up);
            thread::sleep(Duration::from_millis(20));
            CGEventPostToPid(pid, cmd_up);

            CFRelease(cmd_up); CFRelease(v_up); CFRelease(v_dn); CFRelease(cmd_dn);
            CFRelease(src);
        }
    }
}

// ── 读系统剪贴板（pbpaste 比 Tauri plugin 更可靠）──────────────────────────
#[cfg(target_os = "macos")]
fn read_clipboard() -> String {
    Command::new("pbpaste").output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .unwrap_or_default()
}

#[cfg(target_os = "macos")]
fn write_clipboard(text: &str) -> bool {
    let mut child = match Command::new("pbcopy")
        .stdin(std::process::Stdio::piped())
        .spawn()
    {
        Ok(child) => child,
        Err(_) => return false,
    };
    if let Some(stdin) = child.stdin.as_mut() {
        if stdin.write_all(text.as_bytes()).is_err() {
            return false;
        }
    }
    child.wait().map(|s| s.success()).unwrap_or(false)
}

// ── 获取当前最前面的 app 的名称和 PID（macOS）───────────────────────────────
#[cfg(target_os = "macos")]
fn get_frontmost_app() -> (String, i32) {
    let out = Command::new("osascript")
        .arg("-e")
        .arg("tell application \"System Events\"\nset p to first application process whose frontmost is true\nreturn (name of p) & \",\" & (unix id of p)\nend tell")
        .output();
    match out {
        Ok(o) => {
            let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
            let mut parts = s.splitn(2, ',');
            let name = parts.next().unwrap_or("").to_string();
            let pid  = parts.next().and_then(|p| p.trim().parse().ok()).unwrap_or(0);
            (name, pid)
        }
        Err(_) => (String::new(), 0),
    }
}

#[cfg(target_os = "macos")]
fn paste_via_menu(pid: i32) -> bool {
    if pid <= 0 {
        return false;
    }

    let script = format!(
        r#"tell application "System Events"
set p to first process whose unix id is {pid}
tell p
    click menu item "Paste" of menu "Edit" of menu bar 1
end tell
end tell"#
    );

    Command::new("osascript")
        .arg("-e")
        .arg(script)
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

#[cfg(target_os = "macos")]
fn copy_via_menu(pid: i32) -> bool {
    if pid <= 0 {
        return false;
    }

    let script = format!(
        r#"tell application "System Events"
set p to first process whose unix id is {pid}
tell p
    click menu item "Copy" of menu "Edit" of menu bar 1
end tell
end tell"#
    );

    Command::new("osascript")
        .arg("-e")
        .arg(script)
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

// ── 弹出输入框前记住上一个 app，然后显示窗口 ─────────────────────────────────
fn show_input<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    #[cfg(target_os = "macos")]
    {
        let prev = get_frontmost_app();
        debug_log(format!("show_input prev_app={} pid={}", prev.0, prev.1));
        if !prev.0.is_empty() {
            if let Ok(mut g) = app.state::<PreviousApp>().0.lock() {
                *g = prev;
            }
        }
    }
    if let Some(w) = app.get_webview_window("input") {
        show_popup_window(&w, "input")?;
    }
    Ok(())
}

// ── 粘贴文字到之前聚焦的 app ─────────────────────────────────────────────────
#[tauri::command]
fn paste_text(app: AppHandle, text: String) -> Result<(), String> {
    debug_log(format!("paste_text len={}", text.len()));
    #[cfg(target_os = "macos")]
    {
        let mut child = Command::new("pbcopy")
            .stdin(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| e.to_string())?;
        if let Some(stdin) = child.stdin.as_mut() {
            stdin.write_all(text.as_bytes()).map_err(|e| e.to_string())?;
        }
        child.wait().ok();
    }
    #[cfg(not(target_os = "macos"))]
    {
        use tauri_plugin_clipboard_manager::ClipboardExt;
        app.clipboard().write_text(text).map_err(|e| e.to_string())?;
    }

    if let Some(w) = app.get_webview_window("input") {
        w.hide().ok();
    }

    thread::sleep(Duration::from_millis(300));

    #[cfg(target_os = "macos")]
    {
        let (_, pid) = app.state::<PreviousApp>().0.lock().map(|g| g.clone()).unwrap_or_default();
        debug_log(format!("paste_text target_pid={pid}"));

        if pid > 0 {
            Command::new("osascript")
                .arg("-e")
                .arg(format!("tell application \"System Events\" to set frontmost of (first process whose unix id is {pid}) to true"))
                .output().ok();
        }
        thread::sleep(Duration::from_millis(400));

        // Menu paste avoids IME "v mode" when synthetic Cmd+V loses its modifier.
        if paste_via_menu(pid) {
            debug_log("paste_text menu_paste_done");
            let _ = std::fs::write("/tmp/paste_debug.txt", format!("pid={pid}\nmenu paste called\n"));
        } else {
            debug_log("paste_text menu_paste_failed_fallback_cg");
            cg::cmd_v(pid);
            debug_log("paste_text cg_cmd_v_done");
            let _ = std::fs::write("/tmp/paste_debug.txt", format!("pid={pid}\ncg::cmd_v called\n"));
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        thread::sleep(Duration::from_millis(300));
        if let Ok(mut enigo) = Enigo::new(&Settings::default()) {
            enigo.key(Key::Control, enigo::Direction::Press).ok();
            enigo.key(Key::Unicode('v'), enigo::Direction::Click).ok();
            enigo.key(Key::Control, enigo::Direction::Release).ok();
        }
    }

    Ok(())
}

#[tauri::command]
fn get_pending_translate(app: AppHandle) -> String {
    let text = app.state::<PendingTranslate>().0.lock().map(|g| g.clone()).unwrap_or_default();
    debug_log(format!("get_pending_translate len={}", text.len()));
    text
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
        .manage(PreviousApp(Mutex::new((String::new(), 0))))
        .manage(PendingTranslate(Mutex::new(String::new())))
        .setup(|app| {
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            if let Some(w) = app.get_webview_window("input") {
                w.set_visible_on_all_workspaces(true).ok();
                w.set_always_on_top(true).ok();
            }

            // ── 启动 Python backend ──────────────────────────────────────
            let backend_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent().unwrap()
                .parent().unwrap()
                .join("backend");
            let script = backend_dir.join("main.py");
            let python = backend_dir.join(".venv").join("bin").join("python");
            let python = if python.exists() { python } else { std::path::PathBuf::from("python3") };

            let child = Command::new(&python).arg(&script).spawn().ok();
            debug_log(format!("backend_spawn python={} script={} ok={}", python.display(), script.display(), child.is_some()));
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
                        let _ = show_input(tray.app_handle());
                    }
                })
                .build(app)?;

            // ── 快捷键：CapsLock+I → F13 → 输入框（Karabiner 转换，无 Shift，不干扰输入法）──
            let h1 = app.handle().clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(None, Code::F13),
                move |_, _, _| { let _ = show_input(&h1); },
            )?;

            // ── 快捷键：CapsLock+T → F14 → 划词翻译 ─────────────────────
            let h2 = app.handle().clone();
            app.global_shortcut().on_shortcut(
                Shortcut::new(None, Code::F14),
                move |_app, _, _| {
                    debug_log("shortcut_translate fired");
                    #[cfg(target_os = "macos")]
                    let old_clip = read_clipboard();
                    #[cfg(not(target_os = "macos"))]
                    {
                        if let Ok(mut enigo) = Enigo::new(&Settings::default()) {
                            enigo.key(Key::Control, enigo::Direction::Press).ok();
                            enigo.key(Key::Unicode('c'), enigo::Direction::Click).ok();
                            enigo.key(Key::Control, enigo::Direction::Release).ok();
                        }
                    }

                    thread::sleep(Duration::from_millis(300));

                    // Menu Copy avoids IME "c mode" when synthetic Cmd+C loses its modifier.
                    #[cfg(target_os = "macos")]
                    {
                        let (_, pid) = get_frontmost_app();
                        let sentinel = format!("__AI_INPUT_COPY_SENTINEL_{}__", std::process::id());
                        let _ = write_clipboard(&sentinel);
                        let copied = copy_via_menu(pid);
                        thread::sleep(Duration::from_millis(250));
                        let new_clip = read_clipboard().trim().to_string();
                        debug_log(format!("shortcut_translate copy pid={pid} copied={copied} old_len={} new_len={}", old_clip.trim().len(), new_clip.len()));
                        if copied && !new_clip.is_empty() && new_clip != sentinel {
                            let _ = show_translate(&h2, &new_clip);
                        } else {
                            let _ = write_clipboard(&old_clip);
                            debug_log("shortcut_translate skipped empty_or_no_selection");
                        }
                    }
                    #[cfg(not(target_os = "macos"))]
                    {
                        use tauri_plugin_clipboard_manager::ClipboardExt;
                        if let Ok(text) = _app.clipboard().read_text() {
                            let text = text.trim().to_string();
                            if !text.is_empty() {
                                let _ = show_translate(&h2, &text);
                            }
                        }
                    }
                },
            )?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![paste_text, get_pending_translate])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn show_translate<R: Runtime>(app: &AppHandle<R>, text: &str) -> tauri::Result<()> {
    debug_log(format!("show_translate len={}", text.len()));
    if let Ok(mut g) = app.state::<PendingTranslate>().0.lock() {
        *g = text.to_string();
    }

    if let Some(w) = app.get_webview_window("translate") {
        w.eval("window.__reloadTranslate && window.__reloadTranslate()")?;
        return show_popup_window(&w, "translate");
    }

    let w = WebviewWindowBuilder::new(app, "translate", WebviewUrl::App("/translate".into()))
        .title("划词翻译")
        .inner_size(480.0, 140.0)
        .resizable(false)
        .always_on_top(true)
        .build()?;
    show_popup_window(&w, "translate")
}

fn show_or_create<R: Runtime>(app: &AppHandle<R>, label: &str) -> tauri::Result<()> {
    if let Some(w) = app.get_webview_window(label) {
        return show_popup_window(&w, label);
    }

    let (width, height, title) = match label {
        "translate" => (480.0, 140.0, "划词翻译"),
        "review"    => (520.0, 600.0, "复习"),
        "stats"     => (520.0, 500.0, "学习进展"),
        _           => (480.0, 320.0, label),
    };

    let w = WebviewWindowBuilder::new(app, label, WebviewUrl::App(format!("{label}/").into()))
        .title(title)
        .inner_size(width, height)
        .resizable(false)
        .always_on_top(true)
        .build()?;
    show_popup_window(&w, label)
}
