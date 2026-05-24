use lm_studio_api::prelude::*;

/// The system prompt
struct SystemPrompt;

impl SystemInfo for SystemPrompt {
    fn new() -> Box<Self> {
        Box::new(Self {})
    }

    fn update(&mut self) -> String {
        format!(r##""##)
    }
}

pub fn new_chat() -> Chat {
    Chat::new(
        Model::Other("qwen3-4b-instruct-2507".to_string()),
        Context::new(SystemPrompt::new(), 8192),
        1234,
    )
}

pub async fn say(chat: &mut Chat, text: String) -> Result<String> {
    let request = Messages {
        messages: vec![Message {
            role: Role::User,
            content: vec![Content::Text { text }],
        }],
        stream: true,
        context: true,
        skip_think: true,
        ..Default::default()
    };

    let _ = chat.send(request.into()).await?;

    let mut res = String::new();
    while let Some(result) = chat.next().await {
        match result {
            Ok(r) => {
                if let Some(text) = r.text() {
                    // eprint!("{text}");
                    res += text;
                } else {
                }
            }
            Err(e) => eprintln!("Error: {e}"),
        }
    }

    Ok(res)
}
