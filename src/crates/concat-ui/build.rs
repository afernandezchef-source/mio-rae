// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Jareer and Concat contributors

//! Compiles the Slint interface in its own crate to bound peak rustc memory.

fn main() {
    let compile = std::thread::Builder::new()
        .name("slint".into())
        .stack_size(512 << 20)
        .spawn(|| {
            let config = slint_build::CompilerConfiguration::new()
                .embed_resources(slint_build::EmbedResourcesKind::EmbedFiles);
            let entry = if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("android") {
                android_ui_entry().expect("generate Android UI")
            } else {
                "../concat/ui/app.slint".into()
            };
            slint_build::compile_with_config(entry, config)
        })
        .expect("could not start the Slint compiler thread");
    compile
        .join()
        .expect("the Slint compiler thread panicked")
        .expect("failed to compile ui/app.slint");
}

/// Android never instantiates the desktop title bar or four-pane workspace.
/// Keeping their declarations out of the generated Rust reduces its size.
/// Compilation still requires a runner with enough memory. The phone
/// shell and its shared globals/callbacks still come from app.slint.
fn android_ui_entry() -> std::io::Result<std::path::PathBuf> {
    use std::path::PathBuf;
    let source = PathBuf::from("../concat/ui/app.slint");
    println!("cargo:rerun-if-changed={}", source.display());
    let input = std::fs::read_to_string(source)?;
    let begin = "EDITPOP_ANDROID_DESKTOP_BEGIN";
    let end = "EDITPOP_ANDROID_DESKTOP_END";
    let mut output = String::new();
    let mut dropping = false;
    let mut regions = 0;
    for line in input.lines() {
        if line.contains(begin) {
            assert!(!dropping, "nested Android desktop region");
            dropping = true;
            regions += 1;
        } else if line.contains(end) {
            assert!(dropping, "unmatched Android desktop region");
            dropping = false;
        } else if !dropping {
            output.push_str(line);
            output.push('\n');
        }
    }
    assert!(
        !dropping && regions == 4,
        "expected four desktop-only Slint regions"
    );
    let target = PathBuf::from("../concat/ui/.editpop-android.slint");
    if std::fs::read_to_string(&target).ok().as_deref() != Some(output.as_str()) {
        std::fs::write(&target, output)?;
    }
    Ok(target)
}
