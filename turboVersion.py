import time
import re
import os
from ebooklib import epub
import base64
import requests
import json
import anthropic

# ANTHROPIC_API_KEY =
# stability_api_key =

def remove_first_line(text):
    if text.startswith("Here") and text.split("\n")[0].strip().endswith(":"):
        return re.sub(r'^.*\n', '', text, count=1)
    return text

def generate_text(prompt, model="claude-2", max_tokens=2000, temperature=0.7):
    client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
    response = client.completion(
        prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
        model=model,
        max_tokens_to_sample=max_tokens,
        temperature=temperature,
    )
    return response["completion"].strip()

def generate_cover_prompt(plot):
    response = generate_text(
        f"Plot: {plot}\n\n--\n\nDescribe the cover we should create, based on the plot. This should be two sentences long, maximum.")
    return response

def generate_title(plot):
    response = generate_text(
        f"Here is the plot for the book: {plot}\n\n--\n\nRespond with a great title for this book. Only respond with the title, nothing else is allowed.")
    return remove_first_line(response)

def create_cover_image(plot):
# ... (код создания обложки остается без изменений)

def generate_chapter_title(chapter_content):
    response = generate_text(
        f"Chapter Content:\n\n{chapter_content}\n\n--\n\nGenerate a concise and engaging title for this chapter based on its content. Respond with the title only, nothing else.")
    return remove_first_line(response)

def create_epub(title, author, chapters, cover_image_path='cover.png'):
# ... (код создания EPUB остается без изменений)

def generate_chapter(chapter_prompt, chapter_plan, characters, setting, events, model="claude-2", max_tokens=3000, temperature=0.7):
    prompt = f"Chapter Plan: {chapter_plan}\n\nCharacters: {characters}\n\nSetting: {setting}\n\nKey Events: {events}\n\n{chapter_prompt}"
    chapter = generate_text(prompt, model=model, max_tokens=max_tokens, temperature=temperature)

    # Постобработка сгенерированного текста
    chapter = re.sub(r'\n+', '\n', chapter)  # удалить множественные переносы строк
    chapter = re.sub(r'\s+', ' ', chapter)  # удалить множественные пробелы

    return chapter

def generate_book(writing_style, book_description, characters, setting, num_chapters, events):
    print("Generating plot outline...")
    plot_prompt = f"Create a detailed plot outline for a {num_chapters}-chapter book in the {writing_style} style, based on the following description:\n\n{book_description}\n\nEach chapter should be at least 10 pages long."
    plot_outline = generate_text(plot_prompt)
    print("Plot outline generated.")

    chapters = []
    for i in range(num_chapters):
        print(f"Generating chapter {i + 1}...")

        # Генерация плана главы
        chapter_plan_prompt = f"Generate a brief plan for chapter {i+1} based on the following plot outline:\n\n{plot_outline}\n\nFocus on the key events and developments that should occur in this chapter."
        chapter_plan = generate_text(chapter_plan_prompt, max_tokens=500)

        # Генерация главы по частям
        chapter_parts = []

        # Описание
        description_prompt = f"Write a detailed description of the setting and characters for chapter {i+1}, based on the chapter plan:\n\n{chapter_plan}"
        description = generate_chapter(description_prompt, chapter_plan, characters, setting, events)
        chapter_parts.append(description)

        # Диалог
        dialogue_prompt = f"Write an engaging dialogue scene for chapter {i+1}, based on the chapter plan:\n\n{chapter_plan}"
        dialogue = generate_chapter(dialogue_prompt, chapter_plan, characters, setting, events)
        chapter_parts.append(dialogue)

        # Действие
        action_prompt = f"Write an exciting action scene for chapter {i+1}, based on the chapter plan:\n\n{chapter_plan}"
        action = generate_chapter(action_prompt, chapter_plan, characters, setting, events)
        chapter_parts.append(action)

        # Объединение частей главы
        chapter = "\n\n".join(chapter_parts)

        # Редактирование и улучшение главы
        edited_chapter_prompt = f"Please edit and improve the following chapter:\n\n{chapter}\n\nFocus on enhancing the style, coherence, and overall quality of the writing."
        edited_chapter = generate_text(edited_chapter_prompt, model="claude-2", max_tokens=5000, temperature=0.6)

        chapters.append(remove_first_line(edited_chapter))
        print(f"Chapter {i + 1} generated.")

    print("Compiling the book...")
    book = "\n\n".join(chapters)
    print("Book generated!")

    return plot_outline, book, chapters

# Ввод данных пользователем
writing_style = input("Enter the desired writing style: ")
book_description = input("Enter a high-level description of the book: ")
characters = input("Enter a description of the main characters: ")
setting = input("Enter a description of the setting: ")
events = input("Enter a list of key events that should happen in the story: ")
num_chapters = int(input("Enter the number of chapters: "))

# Генерация книги
plot_outline, book, chapters = generate_book(writing_style, book_description, characters, setting, num_chapters, events)

# Интерактивный процесс генерации
user_feedback = input("Are you satisfied with the generated book? (yes/no): ")
while user_feedback.lower() != "yes":
    # Пользователь может выбрать, какую часть книги улучшить
    part_to_improve = input("Which part of the book would you like to improve? (plot/characters/setting/events/specific chapter): ")
    if part_to_improve == "plot":
        new_plot_outline = input("Please provide an updated plot outline: ")
        plot_outline, book, chapters = generate_book(writing_style, book_description, characters, setting, num_chapters, events, new_plot_outline)
    elif part_to_improve == "characters":
        characters = input("Please provide updated character descriptions: ")
        plot_outline, book, chapters = generate_book(writing_style, book_description, characters, setting, num_chapters, events)
    elif part_to_improve == "setting":
        setting = input("Please provide an updated setting description: ")
        plot_outline, book, chapters = generate_book(writing_style, book_description, characters, setting, num_chapters, events)
    elif part_to_improve == "events":
        events = input("Please provide an updated list of key events: ")
        plot_outline, book, chapters = generate_book(writing_style, book_description, characters, setting, num_chapters, events)
    else:
        chapter_num = int(part_to_improve.split(" ")[-1])
        new_chapter = input(f"Please provide an updated version of chapter {chapter_num}: ")
        chapters[chapter_num - 1] = new_chapter
        book = "\n\n".join(chapters)

    user_feedback = input("Are you satisfied with the updated book? (yes/no): ")

title = generate_title(plot_outline)

# Сохранение книги в файл
with open(f"{title}.txt", "w") as file:
    file.write(book)

create_cover_image(plot_outline)

# Создание файла EPUB
create_epub(title, 'AI', chapters, '/content/cover.png')

print(f"Book saved as '{title}.txt'.")