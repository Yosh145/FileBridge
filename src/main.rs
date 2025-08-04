use eframe::{App, Frame, egui};
use egui_file_dialog::FileDialog;
use std::{path::PathBuf, vec};

struct FileBridge {
    selected_file: Option<PathBuf>,
    console_output: Vec<String>,
    file_dialog: FileDialog,
}

impl Default for FileBridge {
    fn default() -> Self {
        Self {
            selected_file: None,
            console_output: vec![format!("FileBridge {}", env!("CARGO_PKG_VERSION"))],
            file_dialog: FileDialog::new(),
        }
    }
}
impl App for FileBridge {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        egui::SidePanel::left("left_panel")
            .resizable(false)
            .min_width(300.0)
            .show(ctx, |ui| {
                ui.heading(format!("FileBridge {}", env!("CARGO_PKG_VERSION")));
                ui.add_space(20.0);

                ui.label("Select File or Folder");

                if ui.button("File/Folder Select").clicked() {
                    self.file_dialog.pick_multiple();
                }

                self.file_dialog.update(ctx);

                ui.label("Selected File or Folder: ");

                ui.label(format!("Picked file: {:?}", self.selected_file))
            });

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Console");
            egui::ScrollArea::vertical().show(ui, |ui| {
                for line in &self.console_output {
                    ui.label(line);
                }
            });
        });
    }
}

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        format!("FileBridge {}", env!("CARGO_PKG_VERSION")).as_str(),
        options,
        Box::new(|_cc| Ok(Box::new(FileBridge::default()))),
    )
}
