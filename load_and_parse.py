import json
import os
from datetime import datetime, timezone
from telethon import TelegramClient, connection
from telethon.errors import SessionPasswordNeededError
import getpass


# КОНФИГУРАЦИЯ
API_ID = 31343652
API_HASH = "a09dd256f40b09a32f385b83ef27f5cc"
PHONE_NUMBER = "+79021269672"

TARGET_CHAT = "+79998847930"  # Юзернейм или телефон собеседника
MY_USER_ID = None  # Заполнится автоматически после входа

MAX_WORDS_PER_DIALOG = 100

OUTPUT_FILE = "dataset.jsonl"
MESSAGES_LIMIT = 10000


async def main():
    # Создаем клиент
    
    client = TelegramClient(
        'anon',
        API_ID,
        API_HASH,

        # Use one of the available connection modes.
        # Normally, this one works with most proxies.
        connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,

        # Then, pass the proxy details as a tuple:
        #     (host name, port, proxy secret)
        proxy=('api-fr4.booksbooks.store', 443, 'ee42307b510f9ba46450cc1bda968fcf3d7777772e676f6f676c652e636f6d')
    )
    
    await client.start(phone=PHONE_NUMBER)
    print("Успешный вход в Telegram")
    
    # Получаем свой ID
    me = await client.get_me()
    my_user_id = me.id
    print(f"Мой ID: {my_user_id}")
    print(f"Имя: {me.first_name} {me.last_name or ''}")
    
    # Получаем свой ID
    me = await client.get_me()
    global MY_USER_ID
    MY_USER_ID = me.id
    print(f"Мой ID: {MY_USER_ID}")
    
    # Получаем диалог
    entity = await client.get_entity(TARGET_CHAT)
    print(f"Найден чат: {entity.id}")

    print(f"Выгружаем сообщения из диалога...")
    
    # Шаг 1: Извлечение, фильтрация и нормализация
    normalized_messages = []
    message_count = 0
    
    async for message in client.iter_messages(entity, reverse=True, limit=MESSAGES_LIMIT):
        message_count += 1
        
        # Фильтрация
        if not message.text:  # Пропускаем нетекстовые сообщения
            continue
        if "http://" in message.text or "https://" in message.text:  # Пропускаем сообщения со ссылками
            continue
        if message.forward is not None:  # Пропускаем пересланные
            continue
        if message.sender_id not in [MY_USER_ID, None]:  # Проверим дальше
            pass
        
        # Определяем отправителя
        if message.sender_id == MY_USER_ID:
            role = "assistant"
        else:
            role = "user"
        
        # Пропускаем системные сообщения без sender_id
        if message.sender_id is None and not message.out:
            continue
        
        normalized_messages.append({
            "role": role,
            "content": message.text,
            "date": message.date
        })
    
    print(f"Всего сообщений: {message_count}")
    print(f"После фильтрации: {len(normalized_messages)}")
    
    if not normalized_messages:
        print("Нет сообщений для обработки")
        return
    
    # Группировка в диалоги
    print(f"Группирую в диалоги (макс. {MAX_WORDS_PER_DIALOG} слов)...")
    dialogues = []
    current_dialogue = []
    current_word_count = 0
    
    for msg in normalized_messages:
        msg_words = len(msg["content"].split())
        
        if not current_dialogue:
            # Начинаем диалог только с user
            if msg["role"] == "user":
                current_dialogue.append(msg.copy())
                current_word_count = msg_words
            continue
        
        last_msg = current_dialogue[-1]
        
        if msg["role"] == last_msg["role"]:
            # Склеиваем сообщения одной роли
            last_msg["content"] += "\n" + msg["content"]
            current_word_count += msg_words
        elif current_word_count + msg_words > MAX_WORDS_PER_DIALOG and last_msg["role"] == "assistant":
            # Завершаем диалог на assistant и начинаем новый
            dialogues.append(current_dialogue)
            current_dialogue = [msg.copy()] if msg["role"] == "user" else []
            current_word_count = msg_words if msg["role"] == "user" else 0
        else:
            current_dialogue.append(msg.copy())
            current_word_count += msg_words
    
    # Добавляем последний диалог, если он заканчивается на user
    if current_dialogue and current_dialogue[-1]["role"] == "assistant" and len(current_dialogue) >= 2:
        dialogues.append(current_dialogue)
    
    print(f"Создано диалогов: {len(dialogues)}")
    
    # Шаг 3: Формирование JSON и запись в файл
    final_count = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for dialogue in dialogues:
            # Убираем техническое поле date и проверяем минимальную длину
            clean_messages = []
            for msg in dialogue:
                if msg["content"].strip():  # Не пустой контент
                    clean_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            if len(clean_messages) < 2:
                continue
            
            # Добавляем system prompt если задан
            messages = []
            if SYSTEM_PROMPT:
                messages.append({"role": "system", "content": SYSTEM_PROMPT})
            
            messages.extend(clean_messages)
            
            # Записываем в файл
            example = {"messages": messages}
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
            final_count += 1
    
    print(f"Готово! Создано диалогов: {final_count}")
    print(f"Файл сохранен: {OUTPUT_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())