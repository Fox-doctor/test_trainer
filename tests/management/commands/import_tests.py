import os
import re
from django.core.management.base import BaseCommand, CommandError
from tests.models import Question


class Command(BaseCommand):
    help = "Импортирует вопросы теста из текстового файла."

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help="Путь к текстовому файлу с вопросами."
        )

    def handle(self, *args, **options):
        filename = options['filename']
        if not os.path.exists(filename):
            raise CommandError(f"Файл '{filename}' не найден.")

        # Попытка прочитать файл с кодировкой UTF-8, если не удаётся — cp1251.
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            self.stdout.write(self.style.WARNING("Не удалось прочитать файл в UTF-8, пробуем cp1251..."))
            try:
                with open(filename, 'r', encoding="cp1251") as f:
                    content = f.read()
            except UnicodeDecodeError:
                raise CommandError("Не удалось прочитать файл с кодировками UTF-8 и cp1251.")

        # Разбиваем файл на строки и обрабатываем первую ненулевую строку для извлечения названия раздела.
        # Разбиваем файл на строки и пытаемся найти строку, содержащую название раздела
        lines = content.splitlines()
        section_name = None
        remaining_lines = []
        for line in lines:
            # Удаляем возможный BOM и лишние пробелы
            line_clean = line.lstrip('\ufeff').strip()
            if line_clean:
                # Приводим строку к нижнему регистру для сравнения
                if line_clean.lower().startswith("раздел:"):
                    # Разбиваем по первому двоеточию и берем всё, что после него
                    section_name = line_clean.split(":", 1)[1].strip()
                else:
                    remaining_lines.append(line)
            else:
                remaining_lines.append(line)
        if not section_name:
            self.stdout.write(
                self.style.WARNING("Название раздела не найдено в файле. Будет использовано значение по умолчанию."))
            section_name = "Неизвестно"

        # Сопоставление названия раздела из файла с одним из предложенных вариантов
        section_mapping = {
            "Мир науки": "world_science",
            "Человек, Земля, Вселенная": "human_earth",
            "Вещества и материалы": "materials",
            "Живая/Неживая природа": "nature",
            "Энергия и движение": "energy_motion",
            "Экология и экосистемы": "ecology",
            "Политическая карта": "politics",
        }
        section_key = section_mapping.get(section_name, section_name)

        # Собираем оставшийся текст (без строки с разделом)
        modified_content = "\n".join(remaining_lines)

        # Разбиваем содержимое на части по разделителю "Правильные ответы:"
        parts = modified_content.split("Правильные ответы:")
        if len(parts) < 2:
            raise CommandError("Разделитель 'Правильные ответы:' не найден в файле.")

        questions_text = parts[0].strip()
        answers_text = parts[1].strip()

        # Извлечение вопросов с вариантами ответов.
        # Ожидаемый формат:
        # 1. Текст вопроса
        # А) вариант1
        # В) вариант2
        # С) вариант3
        # Д) вариант4
        pattern = re.compile(
            r"(\d+)\.\s*(.*?)\n"  # номер вопроса и текст вопроса (вторая группа — текст)
            r"(?:[AА])\)\s*(.*?)\n"  # вариант A (3-я группа)
            r"(?:[BВ])\)\s*(.*?)\n"  # вариант B (4-я группа)
            r"(?:[CС])\)\s*(.*?)\n"  # вариант C (5-я группа)
            r"(?:[DД])\)\s*(.*?)(?:\n|$)",  # вариант D (6-я группа)
            re.DOTALL
        )

        question_matches = pattern.findall(questions_text)
        if not question_matches:
            self.stdout.write(self.style.ERROR("Вопросы не найдены по ожидаемому шаблону."))
            return

        questions_list = []
        for match in question_matches:
            num, question_text, opt1, opt2, opt3, opt4 = match
            questions_list.append({
                'q_num': int(num),
                'question_text': question_text.strip(),
                'option1': opt1.strip(),
                'option2': opt2.strip(),
                'option3': opt3.strip(),
                'option4': opt4.strip(),
            })

        # Обработка правильных ответов, формат:


        answer_dict = {}

        # Исходные строки из блока с правильными ответами
        raw_answer_lines = [line.strip() for line in answers_text.splitlines() if line.strip()]

        # Если в исходном блоке есть двойной перенос строки, считаем, что используется новый формат с блоками
        if "\n\n" in answers_text:
            self.stdout.write("Обнаружен новый формат правильных ответов с блоками.")
            # Разбиваем на блоки по двойному переносу строки
            blocks = [b.strip() for b in answers_text.split("\n\n") if b.strip()]
            for block in blocks:
                tokens = [token.strip() for token in block.splitlines() if token.strip()]
                # Ожидается, что в блоке количество строк чётное (номерной блок и блок с ответами).
                if len(tokens) % 2 != 0:
                    self.stdout.write(self.style.WARNING(f"В блоке ответов нечетное число строк: {tokens}"))
                    continue
                n = len(tokens) // 2
                numbers = tokens[:n]
                letters = tokens[n:]
                if len(numbers) != len(letters):
                    self.stdout.write(
                        self.style.WARNING(f"Несовпадение количества номеров и ответов в блоке: {tokens}"))
                    continue
                for num_str, letter in zip(numbers, letters):
                    try:
                        q_num = int(num_str)
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Не удалось преобразовать '{num_str}' в номер вопроса."))
                        continue
                    answer_dict[q_num] = letter.upper()
                    self.stdout.write(f"  -> Parsed: question {q_num} -> answer {letter.upper()}")
        else:
            self.stdout.write("Используется старый формат правильных ответов.")
            # Обработка старого формата, когда каждая строка содержит пару вида "1Д", "1 Д", "1. Д" и т.п.
            for idx, line in enumerate(raw_answer_lines):
                self.stdout.write(f"Line {idx + 1}: '{line}'")
                m = re.match(r"(\d+)[\.\s-]*([A-DАВСД])", line, re.IGNORECASE)
                if m:
                    q_num = int(m.group(1))
                    letter = m.group(2).upper()
                    answer_dict[q_num] = letter
                    self.stdout.write(f"  -> Parsed: question {q_num} -> answer {letter}")
                else:
                    self.stdout.write("  -> No match for this line")

        self.stdout.write("Final answer dictionary:")
        self.stdout.write(str(answer_dict))

        # Словарь для преобразования буквы в номер варианта.
        mapping = {
            "A": 1, "А": 1,
            "B": 2, "В": 2,
            "C": 3, "С": 3,
            "D": 4, "Д": 4,
        }

        created = 0
        for question_data in questions_list:
            q_num = question_data.get('q_num')
            letter = answer_dict.get(q_num)
            if letter:
                correct_option = mapping.get(letter, 1)
            else:
                correct_option = 1

            question_obj = Question(
                question_text=question_data['question_text'],
                subject='science',
                section=section_key,
                option1=question_data['option1'],
                option2=question_data['option2'],
                option3=question_data['option3'],
                option4=question_data['option4'],
                correct_option=correct_option,
            )
            question_obj.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Успешно импортировано {created} вопросов для раздела '{section_name}'!"))
