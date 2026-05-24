import json
import ollama
from datasets import load_dataset, concatenate_datasets

SYSTEM_PROMPT = "Ты — Алиса. Отвечай коротко, со сленгом."
NUM_EXAMPLES = 10
MAX_TURNS = 20

# ЗАГРУЗКА ОРИГИНАЛЬНОГО ДАТАСЕТА
dataset = load_dataset("json", data_files="dataset.jsonl", split="train")
print(f"Оригинальный датасет: {len(dataset)} диалогов")

# ПОДГОТОВКА ПРИМЕРОВ ДЛЯ МОДЕЛИ
def format_dialog_for_prompt(messages):
    lines = []
    for msg in messages:
        if msg["role"] != "system":
            lines.append(f"{msg['role']}: {msg['content']}")
    return "\n".join(lines)


def prepare_examples(dataset, num_examples):
    import random
    
    indices = random.sample(range(len(dataset)), min(num_examples, len(dataset)))
    
    parts = []
    for i, idx in enumerate(indices):
        dialog_text = format_dialog_for_prompt(dataset[idx]["messages"])
        parts.append(f"Диалог {i+1}\n{dialog_text}")
    
    return "\n\n".join(parts)

examples_text = prepare_examples(dataset, num_examples=NUM_EXAMPLES)

# ГЕНЕРАЦИЯ СИНТЕТИКИ ЧЕРЕЗ OLLAMA
print("Генерирую синтетические диалоги...")

prompt = f"""Твоя задача — сгенерировать диалоги В ТОЧНО ТАКОМ ЖЕ СТИЛЕ, как примеры ниже:

{examples_text}

СТИЛЬ:
- Короткие фразы, часто без знаков препинания
- Некоторые слова с опечатками: "хоршо", "дп", "умни"
- Использует сленг: "хз", "наверн", "треш", "комп"
- Неформальное общение: "дада", "вово", "приви"

Сгенерируй 5 новых диалогов. Меняй темы. Каждый диалог — 2-6 реплик, заканчивается ответом ассистента.

Верни новые диалоги в ТОЧНО ТАКОМ ЖЕ ФОРМАТЕ как примеры выше:
Диалог 1
user: реплика
assistant: ответ
user: реплика
assistant: ответ

Диалог 2
user: реплика
assistant: ответ

Каждый диалог начинается с Диалог N
Заканчивается ответом assistant.
Больше ничего не пиши.
"""

raw_text = ""

for i in range(MAX_TURNS):
    response = ollama.generate(
        model="qwen2.5:7b",
        prompt=prompt,
        options={
            "temperature": 0.9,
            "num_predict": 2000,
        }
    )
    raw_text += response["response"] + "\n"

print(f"Получен ответ от модели ({len(raw_text)} символов)")

# ПАРСИНГ ОТВЕТА
synthetic = []
current_dialog = []
current_role = None

for line in raw_text.split("\n"):
    line = line.strip()
    
    # Новый диалог
    if line.startswith("Диалог"):
        # Сохраняем предыдущий
        if current_dialog and current_dialog[-1]["role"] == "assistant":
            # Добавляем system в начало
            current_dialog.insert(0, {
                "role": "system",
                "content": SYSTEM_PROMPT
            })
            synthetic.append({"messages": current_dialog})
        current_dialog = []
        continue
    
    # Реплика пользователя
    if line.startswith("user: "):
        content = line[6:]  # Убираем "user: "
        current_dialog.append({"role": "user", "content": content})
    
    # Ответ ассистента
    elif line.startswith("assistant: "):
        content = line[11:]  # Убираем "assistant: "
        current_dialog.append({"role": "assistant", "content": content})

# Последний диалог
if current_dialog and current_dialog[-1]["role"] == "assistant":
    current_dialog.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    synthetic.append({"messages": current_dialog})

print(f"Распарсено: {len(synthetic)} диалогов")

# СОХРАНЕНИЕ СИНТЕТИКИ
with open("synthetic.jsonl", "w", encoding="utf-8") as f:
    for example in synthetic:
        f.write(json.dumps(example, ensure_ascii=False) + "\n")

print("Сохранено в synthetic.jsonl")

# ЗАГРУЗКА И ОБЪЕДИНЕНИЕ
synthetic_dataset = load_dataset("json", data_files="synthetic.jsonl", split="train")
combined = concatenate_datasets([dataset, synthetic_dataset])
combined = combined.shuffle(seed=42)

# СОХРАНЕНИЕ ОБЪЕДИНЁННОГО
combined.to_json("combined_dataset.jsonl", force_ascii=False)