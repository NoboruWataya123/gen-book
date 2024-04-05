import time
import re
import os
from ebooklib import epub
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
stability_api_key = os.getenv('STABILITY_API_KEY')


def remove_first_line(test_string):
    if test_string.startswith("Here") and test_string.split("\n")[0].strip().endswith(":"):
        return re.sub(r'^.*\n', '', test_string, count=1)
    return test_string


def generate_text(prompt, model="claude-3-opus-20240229", max_tokens=2000, temperature=0.7):
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": "Вы - всемирно известный русскоязычный писатель. Ваша задача - создавать увлекательный, связный и грамматически правильный текст на русском языке с большим мастерством и вниманием к деталям.",
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
    response.raise_for_status()
    response_text = response.json()['content'][0]['text']
    return response_text.strip()


def generate_cover_prompt(plot):
    response = generate_text(
        f"Сюжет: {plot}\n\n--\n\nОпишите подробно, какой должна быть обложка книги, основываясь на приведенном сюжете. Обложка должна привлекать внимание и отражать ключевые моменты сюжета. Опишите цвета, композицию и основные элементы, которые должны присутствовать на обложке. Текст должен быть на русском языке и состоять из 3-4 предложений.")
    return response


def generate_title(plot):
    response = generate_text(
        f"Вот сюжет книги: {plot}\n\n--\n\nПридумайте креативное, запоминающееся и интригующее название для этой книги на русском языке. Название должно отражать суть сюжета и привлекать потенциальных читателей. Отвечайте только названием книги, без дополнительного текста.")
    return remove_first_line(response)


def create_cover_image(plot):
    plot = str(generate_cover_prompt(plot))

    engine_id = "stable-diffusion-xl-beta-v2-2-2"
    api_host = os.getenv('API_HOST', 'https://api.stability.ai')
    api_key = stability_api_key

    if api_key is None:
        raise Exception("Missing Stability API key.")

    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "text_prompts": [
                {
                    "text": plot
                }
            ],
            "cfg_scale": 7,
            "clip_guidance_preset": "FAST_BLUE",
            "height": 768,
            "width": 512,
            "samples": 1,
            "steps": 30,
        },
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    for i, image in enumerate(data["artifacts"]):
        cover_image_path = os.path.join(os.path.dirname(__file__), "cover.png")
        with open(cover_image_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))


def generate_chapter_title(chapter_content):
    response = generate_text(
        f"Содержание главы:\n\n{chapter_content}\n\n--\n\nСоздайте краткое, информативное и привлекательное название для этой главы на русском языке, основываясь на ее содержании. Название должно отражать ключевые события или тему главы. Отвечайте только названием главы, без дополнительного текста.")
    return remove_first_line(response)


def sanitize_title(s_title):
    # Remove invalid characters for file names
    san_title = re.sub(r'[<>:"/\\|?*]', '', s_title)
    # Replace spaces with underscores
    san_title = san_title.replace(' ', '_')
    return san_title


def create_epub(title_epub, author, chapters_epub, cover_image_path='cover.png'):
    book_epub = epub.EpubBook()
    # Set metadata
    book_epub.set_identifier('id123456')
    book_epub.set_title(title_epub)
    book_epub.set_language('ru')
    book_epub.add_author(author)
    # Add cover image
    cover_image_path = os.path.join(os.path.dirname(__file__), cover_image_path)
    with open(cover_image_path, 'rb') as cover_file:
        cover_image = cover_file.read()
    book_epub.set_cover('cover.png', cover_image)
    # Create chapters and add them to the book
    epub_chapters = []
    for i, chapter_content in enumerate(chapters_epub):
        chapter_title = generate_chapter_title(chapter_content)
        chapter_file_name = f'chapter_{i + 1}.xhtml'
        epub_chapter = epub.EpubHtml(title=chapter_title, file_name=chapter_file_name, lang='ru')
        # Add paragraph breaks
        formatted_content = ''.join(
            f'<p>{paragraph.strip()}</p>' for paragraph in chapter_content.split('\n') if paragraph.strip())
        epub_chapter.content = f'<h1>{chapter_title}</h1>{formatted_content}'
        book_epub.add_item(epub_chapter)
        epub_chapters.append(epub_chapter)

    # Define Table of Contents
    book_epub.toc = epub_chapters

    # Add default NCX and Nav files
    book_epub.add_item(epub.EpubNcx())
    book_epub.add_item(epub.EpubNav())

    # Define CSS style
    style = '''
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: Cambria, Liberation Serif, serif;
    }
    h1 {
        text-align: left;
        text-transform: uppercase;
        font-weight: 200;
    }
    '''

    # Add CSS file
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book_epub.add_item(nav_css)

    # Create spine
    book_epub.spine = ['nav'] + epub_chapters

    # Save the EPUB file
    epub_file_path = os.path.join(os.path.dirname(__file__), f'{title_epub}.epub')
    epub.write_epub(epub_file_path, book_epub)


def generate_book(gen_writing_style, gen_book_description, gen_num_chapters):
    print("Создание детальной схемы сюжета...")
    plot_prompt = f"Создайте подробную схему сюжета для книги из {gen_num_chapters} глав в стиле {gen_writing_style}, основываясь на следующем описании:\n\n{gen_book_description}\n\nСхема должна включать завязку, развитие сюжета, кульминацию и развязку. Каждая глава должна быть не менее 10 страниц. Текст должен быть на русском языке."
    gen_plot_outline = generate_text(plot_prompt)
    print("Схема сюжета создана.")

    gen_chapters = []
    for i in range(gen_num_chapters):
        print(f"Создание главы {i + 1}...")
        chapter_prompt = f"Предыдущие главы:\n\n{' '.join(gen_chapters)}\n\nСтиль написания: `{gen_writing_style}`\n\nСхема сюжета:\n\n{gen_plot_outline}\n\nНапишите главу {i + 1} книги на русском языке, убедившись, что она соответствует схеме сюжета, опирается на предыдущие главы и продвигает историю вперед. Глава должна быть написана увлекательно, с интересными диалогами и описаниями. Используйте богатую и разнообразную лексику, чтобы полностью погрузить читателя в происходящее. Глава должна состоять не менее чем из 50 абзацев, мы стремимся к насыщенным и захватывающим главам."
        chapter = generate_text(chapter_prompt, max_tokens=4000)
        gen_chapters.append(remove_first_line(chapter))
        print(f"Глава {i + 1} создана.")
        time.sleep(65)  # Добавьте небольшую задержку, чтобы избежать превышения лимитов

    print("Compiling the book...")
    gen_book = "\n\n".join(gen_chapters)
    print("Book generated!")

    return gen_plot_outline, gen_book, gen_chapters


# User input
writing_style = input("Enter the desired writing style: ")
book_description = input("Enter a high-level description of the book: ")
num_chapters = int(input("Enter the number of chapters: "))

# Generate the book
plot_outline, book, chapters = generate_book(writing_style, book_description, num_chapters)

title = generate_title(plot_outline)
sanitized_title = sanitize_title(title)

# Save the book to a file
with open(f"{sanitized_title}.txt", "w") as file:
    file.write(book)

create_cover_image(plot_outline)

# Create the EPUB file
create_epub(sanitized_title, 'AI', chapters, 'cover.png')

print(f"Book saved as '{sanitized_title}.txt'.")
