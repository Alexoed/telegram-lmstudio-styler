use std::{collections::BTreeMap, fs, sync::Arc};

use lm_studio_api::prelude::Chat;
use teloxide::{
    prelude::*,
    requests::HasPayload,
    sugar::bot::BotMessagesExt,
    types::{MediaKind, MessageKind, ReactionType},
};
mod back;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    let bot = Bot::new(fs::read_to_string("token.txt").expect("Couldn't read token"));

    let dialogs: Arc<Mutex<BTreeMap<i64, Chat>>> = Arc::new(Mutex::new(BTreeMap::new()));

    let handler = Update::filter_message().endpoint(
        |bot: Bot, dialogs: Arc<Mutex<BTreeMap<i64, Chat>>>, msg: Message| async move {
            if let MessageKind::Common(t) = &msg.kind {
                if let MediaKind::Text(text) = &t.media_kind {
                    println!("Получено: {} (chat.id: {})", text.text, msg.chat.id.0);
                    let response;
                    let key = msg.chat.id.0;
                    let mut d = dialogs.lock().await;
                    if let Some(c) = d.get_mut(&key) {
                        if text.text == "/exit" {
                            response = "Диалог забыт".to_string();
                            d.remove(&key);
                        } else {
                            response = back::say(c, text.text.clone()).await.unwrap();
                        }
                    } else {
                        let mut c = back::new_chat();
                        if text.text == "/start" {
                            response = "Диалог создан".to_string();
                        } else {
                            response = back::say(&mut c, text.text.clone()).await.unwrap();
                        }
                        d.insert(key, c);
                    }
                    drop(d);
                    println!("Отвечаем: {response}");
                    bot.send_message(msg.chat.id, response).await?;
                } else {
                    println!("Попытка поставить реакцию");
                    bot.set_reaction(&msg)
                        .with_payload_mut(|f| {
                            f.reaction = Some(vec![ReactionType::Emoji {
                                emoji: "🤯".to_string(),
                            }]);
                            // f.is_big = Some(true);
                        })
                        .await?;
                }
            } else {
                println!("Не знаем таких");
                bot.send_dice(msg.chat.id).await?;
            }
            respond(())
        },
    );

    Dispatcher::builder(bot, handler)
        // Pass the shared state to the handler as a dependency.
        .dependencies(dptree::deps![dialogs])
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;
}
