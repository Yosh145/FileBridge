use std::env;
use std::fs::File;

use iced::{Element, Sandbox, Settings};
use iced::widget::text;

fn main() -> iced::Result {
    FileBridge::run(Settings::default())
}

struct FileBridge;

#[derive(Debug)]
enum Message {}

impl Sandbox for FileBridge {
    type Message = Message;

    fn new() -> Self {
        Self
    }

    fn title(&self) -> String {
        let cargo_pkg: String = env!("CARGO_PKG_VERSION").into();
        let mut title = String::from("FileBridge ");
        title.push_str(&cargo_pkg);

        return title;
    }

    fn update(&mut self, message: Self::Message) {
        match message {}
    }

    fn view(&self) -> Element<'_, Self::Message> {
        text("Test").into()
    }
}
