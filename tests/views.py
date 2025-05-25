from django.shortcuts import get_object_or_404, render, redirect
from .models import Question, TestResult, SUBJECT_CHOICES, SECTION_CHOICES
from django.contrib.auth.decorators import login_required, user_passes_test  # импорт декоратора
from .forms import TestSelectionForm, QuestionForm
from django.urls import reverse
from django.contrib import messages
import json, re
from django.contrib.auth.models import User
from .forms import UserEditForm
from .models import Profile
from django.db.models import Avg, Max, Min
from .models import TrainingTestResult
from .constants import SUBJECT_MAPPING, SECTION_MAPPING
from django.contrib.admin.views.decorators import staff_member_required


@login_required
def user_statistics(request):
    user = request.user
    # Значения по умолчанию – реальные метки, сохранённые в базе данных
    subject = request.GET.get('subject', 'Естествознание').strip()
    section = request.GET.get('section', 'Мир науки').strip()

    # Фильтрация тестовых результатов по выбранным значениям
    results = TestResult.objects.filter(user=user, subject=subject, section=section).order_by('date')

    total_tests = results.count()
    avg_score = results.aggregate(Avg('score'))['score__avg'] or 0
    best_score = results.aggregate(Max('score'))['score__max'] or 0
    worst_score = results.aggregate(Min('score'))['score__min'] or 0

    progress_data = list(results.values('date', 'score'))
    progress_json = json.dumps(progress_data, default=str)

    context = {
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'worst_score': worst_score,
        'progress_data': progress_json,
        'subject': subject,
        'section': section,
        'subject_choices': SUBJECT_CHOICES,
        'section_choices': SECTION_CHOICES,
    }
    return render(request, 'tests/progress.html', context)



def is_moderator(user):
    # Вы можете настроить логику проверки: например, если пользователь - сотрудник или в группе модераторов.
    return user.is_staff or user.groups.filter(name='moderators').exists()

@login_required
@user_passes_test(is_moderator)
def question_list(request):
    # Начинаем с базового запроса
    questions = Question.objects.all()

    # Получаем параметры фильтрации и поиска из GET-запроса
    subject_filter = request.GET.get('subject', '')
    section_filter = request.GET.get('section', '')
    search_query = request.GET.get('q', '')
    ordering = request.GET.get('ordering', 'id')  # по умолчанию сортировка по id

    if subject_filter:
        questions = questions.filter(subject=subject_filter)
    if section_filter:
        questions = questions.filter(section=section_filter)
    if search_query:
        questions = questions.filter(question_text__icontains=search_query)

    # Разрешённые поля для сортировки
    allowed_ordering = ['id', 'subject', 'section', 'question_text']
    if ordering in allowed_ordering:
        questions = questions.order_by(ordering)
    else:
        questions = questions.order_by('id')

    context = {
        'questions': questions,
        'subject_filter': subject_filter,
        'section_filter': section_filter,
        'search_query': search_query,
        'ordering': ordering,
        # Передаём списки вариантов для полей, чтобы сформировать выпадающие списки
        'subject_choices': Question._meta.get_field('subject').choices,
        'section_choices': Question._meta.get_field('section').choices,
    }
    return render(request, 'tests/question_list.html', context)



@login_required
@user_passes_test(is_moderator)
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Вопрос успешно создан!")
            return redirect('question_list')
    else:
        form = QuestionForm()
    return render(request, 'tests/question_form.html', {'form': form, 'title': 'Добавить вопрос'})

@login_required
@user_passes_test(is_moderator)
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, "Вопрос успешно обновлён!")
            return redirect('question_list')
    else:
        form = QuestionForm(instance=question)
    return render(request, 'tests/question_form.html', {'form': form, 'title': 'Редактировать вопрос'})

@login_required
@user_passes_test(is_moderator)
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Вопрос успешно удалён!")
        return redirect('question_list')
    return render(request, 'tests/question_confirm_delete.html', {'question': question})

def home(request):
    return render(request, 'tests/home.html')


def select_test(request):
    """Представление для выбора предмета и раздела теста."""
    if request.method == 'POST':
        form = TestSelectionForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            section = form.cleaned_data['section']
            test_mode = request.POST.get('test_mode')  # Получаем значение кнопки
            if test_mode == 'training':
                # Для тренажёрного теста – перенаправляем на представление training_test
                url = reverse('training_test')
            else:
                # По умолчанию (например, когда нажата кнопка "Контрольный тест")
                url = reverse('test_page')
            # Добавляем параметры выбора в URL
            return redirect(f"{url}?subject={subject}&section={section}")
    else:
        form = TestSelectionForm()
    return render(request, 'tests/select_test.html', {'form': form})


@login_required  # Этот декоратор ограничит доступ к представлению только для авторизованных пользователей.
def training_test(request):
    subject = request.GET.get('subject')
    section = request.GET.get('section')
    stored_subject = request.session.get('training_subject')
    stored_section = request.session.get('training_section')

    # Сбрасываем тест, если пришли новые параметры или тест уже не завершён
    if request.method == 'GET' and subject and section and (
            stored_subject != subject or stored_section != section):
        request.session.pop('training_test_ids', None)
        request.session.pop('training_current_index', None)
        request.session.pop('training_answers', None)
        request.session['training_subject'] = subject
        request.session['training_section'] = section
        request.session.pop('training_result_saved', None)

    # Если в сессии ещё нет списка вопросов, создаём его
    if 'training_test_ids' not in request.session:
        training_subject = request.session.get('training_subject')
        training_section = request.session.get('training_section')
        question_ids = list(
            Question.objects.filter(subject=training_subject, section=training_section)
            .order_by('?')
            .values_list('id', flat=True)[:20]
        )
        request.session['training_test_ids'] = question_ids
        request.session['training_current_index'] = 0
        request.session['training_answers'] = {}


    # Последующая логика без изменений...
    question_ids = request.session['training_test_ids']
    current_index = request.session.get('training_current_index', 0)
    total_questions = len(question_ids)

    if current_index >= total_questions:
        return redirect(reverse('training_results'))

    current_question_id = question_ids[current_index]
    question = get_object_or_404(Question, id=current_question_id)

    feedback = None
    chosen_answer = None

    if request.method == 'POST':
        if 'defer' in request.POST:
            question_ids.append(question_ids.pop(current_index))
            request.session['training_test_ids'] = question_ids
            return redirect(reverse('training_test'))
        elif 'next' in request.POST:
            request.session['training_current_index'] = current_index + 1
            return redirect(reverse('training_test'))
        elif 'check' in request.POST:
            if 'answer' in request.POST:
                chosen_answer = request.POST.get('answer')
                try:
                    is_correct = int(chosen_answer) == question.correct_option
                except (ValueError, TypeError):
                    is_correct = False
                feedback = "Верно!" if is_correct else "Неверно!"
                training_answers = request.session.get('training_answers', {})
                training_answers[str(current_question_id)] = {'answer': chosen_answer, 'is_correct': is_correct}
                request.session['training_answers'] = training_answers

    context = {
        'question': question,
        'feedback': feedback,
        'chosen_answer': chosen_answer,
        'current_index': current_index + 1,
        'total_questions': total_questions,
    }
    return render(request, 'tests/training_test.html', context)


@login_required  # Этот декоратор ограничит доступ к представлению только для авторизованных пользователей.
def training_results(request):
    # Получаем список всех вопросов теста из сессии
    training_test_ids = request.session.get('training_test_ids', [])
    # Получаем данные ответов (если пользователь ответил — иначе запись отсутствует)
    training_answers = request.session.get('training_answers', {})

    results = []
    correct_answers = 0

    # Итерируем по всем идентификаторам вопросов, чтобы получить 20 записей
    for qid in training_test_ids:
        question = get_object_or_404(Question, id=qid)
        # Попытаемся найти данные ответа для данного вопроса; ключи в training_answers хранятся как строки
        answer_data = training_answers.get(str(qid))
        if answer_data:
            selected_option = answer_data.get('answer')
            is_correct = answer_data.get('is_correct')
        else:
            selected_option = None
            is_correct = False

        # Опции ответа
        options = {
            1: question.option1,
            2: question.option2,
            3: question.option3,
            4: question.option4,
        }

        # Если ответ дан, берем его текст, иначе выводим, что не отвечено
        if selected_option and str(selected_option).isdigit():
            selected_text = options.get(int(selected_option), "Не отвечено")
        else:
            selected_text = "Не отвечено"

        correct_text = options.get(question.correct_option, "")

        if is_correct:
            correct_answers += 1

        results.append({
            'question_text': question.question_text,
            'selected_text': selected_text,
            'correct_text': correct_text,
            'is_correct': is_correct,
        })

    # Общее количество вопросов берем исходя из списка идентификаторов
    total_questions = len(training_test_ids)

    # Берем предмет и раздел из сессии и локализуем их согласно общему словарю
    subject = request.session.get('training_subject', '')
    section = request.session.get('training_section', '')
    localized_subject = SUBJECT_MAPPING.get(subject, subject)
    localized_section = SECTION_MAPPING.get(section, section)

    # Сохраняем результат в базу только один раз (чтобы избежать дублирования при обновлении страницы)
    if not request.session.get('training_result_saved'):
        TrainingTestResult.objects.create(
            user=request.user if request.user.is_authenticated else None,
            subject=localized_subject,
            section=localized_section,
            score=correct_answers,
            total_questions=total_questions,
            details=json.dumps(results, ensure_ascii=False)
        )
        request.session['training_result_saved'] = True

    context = {
        'results': results,
        'score': correct_answers,
        'total_questions': total_questions
    }
    return render(request, 'tests/training_results.html', context)


@login_required  # Этот декоратор ограничит доступ к представлению только для авторизованных пользователей.
def training_statistics(request):
    # Получаем историю результатов тренажёрных тестов текущего пользователя
    if request.user.is_authenticated:
        stats = TrainingTestResult.objects.filter(user=request.user).order_by('-taken_at')
    else:
        stats = TrainingTestResult.objects.none()
    context = {
        'stats': stats
    }
    return render(request, 'tests/training_statistics.html', context)

@login_required  # Этот декоратор ограничит доступ к представлению только для авторизованных пользователей.
def test_view(request):
    if request.method == "POST":
        total_questions = 0
        correct_answers = 0
        results = []

        # Проходим по всем данным POST, отбирая ключи с префиксом "question_"
        for key, value in request.POST.items():
            if key.startswith("question_"):
                question_id = key.split("_")[1]
                try:
                    question = Question.objects.get(pk=question_id)
                except Question.DoesNotExist:
                    continue
                total_questions += 1
                selected_option = int(value)  # Преобразуем выбранное значение в число
                is_correct = (selected_option == question.correct_option)

                options = {
                    1: question.option1,
                    2: question.option2,
                    3: question.option3,
                    4: question.option4,
                }
                selected_text = options.get(selected_option, "")
                correct_text = options.get(question.correct_option, "")

                if is_correct:
                    correct_answers += 1

                results.append({
                    'question_text': question.question_text,
                    'selected_text': selected_text,
                    'correct_text': correct_text,
                    'is_correct': is_correct,
                })

        # Сохранение результата теста. Если пользователь аутентифицирован, привяжем результат к нему.
        subject = request.POST.get('subject', '')
        section = request.POST.get('section', '')
        # Дополнительно можно сохранить подробности теста в формате JSON:
        details_json = json.dumps(results, ensure_ascii=False)

        TestResult.objects.create(
            user=request.user if request.user.is_authenticated else None,
            subject=subject,
            section=section,
            score=correct_answers,
            total_questions=total_questions,
            details=details_json,
        )

        context = {
            'results': results,
            'score': correct_answers,
            'total_questions': total_questions
        }
        return render(request, 'tests/results.html', context)
    else:
        # Если запрос GET, выбираем (например) 10 вопросов по умолчанию
        questions = Question.objects.filter(subject='science', section='world_science')[:10]
        context = {
            'questions': questions
        }
        return render(request, 'tests/test_page.html', context)


@login_required  # Этот декоратор ограничит доступ к представлению только для авторизованных пользователей.
def test_page(request):
    """Представление для прохождения теста."""
    subject = request.GET.get('subject')
    section = request.GET.get('section')
    if not subject or not section:
        message = "Необходимо выбрать предмет и раздел."
        return render(request, 'tests/no_questions.html', {'message': message})

    questions = Question.objects.filter(subject=subject, section=section)
    if not questions.exists():
        message = "Вопросы для данного предмета или раздела еще не внесены и находятся на стадии разработки."
        return render(request, 'tests/no_questions.html', {'message': message})

    # Если предмет - естествознание, выбираем случайные 20 вопросов.
    if subject == 'science':
        questions = questions.order_by('?')[:20]
    else:
        questions = questions.order_by('?')

    # Сопоставление ключей раздела с читаемыми названиями
    human_section = SECTION_MAPPING.get(section, section)
    human_subject = SUBJECT_MAPPING.get(subject, subject)

    return render(request, 'tests/test_page.html', {
        'questions': questions,
        'subject': human_subject,  # Читаемое название предмета
        'section': human_section,  # Читаемое название раздела
    })



@login_required
def my_results(request):
    # Получаем все результаты тестов для текущего пользователя, сортируя по дате (сначала самые свежие)
    results = TestResult.objects.filter(user=request.user).order_by('-date')
    return render(request, 'tests/my_results.html', {'results': results})


# Функция-проверка для доступа к администрированию (уже используется)
def is_user_admin(user):
    return user.is_superuser or user.groups.filter(name="Admins").exists()

@login_required
@user_passes_test(is_user_admin)
def user_admin_view(request):
    # Здесь можно добавить логику для обработки временных доступов, формы и т.д.
    users = User.objects.all().order_by('username')
    return render(request, "tests/user_admin.html", {"users": users})


@login_required
@user_passes_test(is_user_admin)
def edit_user_view(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    # Если профиль отсутствует, get_or_create его создаст
    profile, created = Profile.objects.get_or_create(user=user_obj)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj, profile=profile)
        if form.is_valid():
            form.save()
            return redirect('user_admin')  # Возвращаемся на страницу управления
    else:
        form = UserEditForm(instance=user_obj, profile=profile)
    return render(request, 'tests/edit_user.html', {'form': form, 'user_obj': user_obj})


# Загрузка данных из текстового файла
@staff_member_required
def import_questions_text(request):
    import re  # Импортируем модуль re сразу в начале функции
    """
    Импорт вопросов из текстового файла.

    Этап 1 (загрузка файла):
    - Читается файл, извлекаются первые 2 строки (предмет и раздел), затем парсятся блоки вопросов
      и блок с правильными ответами.
    - Парсится каждый блок, ожидается, что в каждом блоке 5 строк: первая — вопрос, далее 4 строки с вариантами.
    - Из блока правильных ответов (после строки "Правильные ответы:") берется последний символ каждой строки
      (сопоставляется с A/А → 1, B/В → 2, C/С → 3, D → 4).
    - Извлечённые данные (предмет, раздел, список вопросов) сохраняются в сессии и показываются на странице подтверждения.

    Этап 2 (подтверждение):
    - Модератор может изменить предмет и раздел (если необходимо) и подтвердить импорт.
    - После подтверждения вопросы записываются в базу.
    """
    if request.method == 'POST':
        if 'confirm' in request.POST:
            # Этап подтверждения импорта
            data = request.session.get('import_questions_data')
            if not data:
                return render(request, 'tests/import_questions_text.html', {'error': 'Нет данных для импорта.'})
            from .constants import SUBJECT_MAPPING, SECTION_MAPPING
            inverted_subject = {v: k for k, v in SUBJECT_MAPPING.items()}
            inverted_section = {v: k for k, v in SECTION_MAPPING.items()}

            new_subject_input = request.POST.get('subject', data['subject']).strip()
            new_section_input = request.POST.get('section', data['section']).strip()

            # Преобразуем входящие значения в ключи для модели
            new_subject = inverted_subject.get(new_subject_input, new_subject_input)
            new_section = inverted_section.get(new_section_input, new_section_input)

            print("Импортируем предмет:", new_subject)  # Должен вывести ключ, например, "science"
            print("Импортируем раздел:", new_section)  # Например, "political_map"

            questions_data = data['questions']
            imported_count = 0
            for q in questions_data:
                Question.objects.create(
                    subject=new_subject,
                    section=new_section,
                    question_text=q['question_text'],
                    option1=q['options'][0] if len(q['options']) > 0 else '',
                    option2=q['options'][1] if len(q['options']) > 1 else '',
                    option3=q['options'][2] if len(q['options']) > 2 else '',
                    option4=q['options'][3] if len(q['options']) > 3 else '',
                    correct_option=q.get('correct_option', 1)
                )
                imported_count += 1
            request.session.pop('import_questions_data', None)
            return render(request, 'tests/import_questions_result.html',
                          {'message': f"Импортировано вопросов: {imported_count}"})
        else:
            # Этап загрузки файла
            file = request.FILES.get('import_file')
            if not file:
                return render(request, 'tests/import_questions_text.html', {'error': 'Файл не выбран.'})
            try:
                content = file.read().decode('utf-8')
            except Exception as e:
                return render(request, 'tests/import_questions_text.html', {'error': f"Ошибка чтения файла: {e}"})

            # Разбиваем содержимое по блокам (разделителем – два или более переносов строки)
            blocks = [block.strip() for block in re.split(r'\n\s*\n', content) if block.strip()]
            if not blocks or len(blocks) < 3:
                return render(request, 'tests/import_questions_text.html', {'error': 'Неверный формат файла.'})

            # Первый блок – заголовок, содержащий предмет и раздел
            header_lines = [line.strip() for line in blocks[0].splitlines() if line.strip()]
            # Удаляем BOM, если он присутствует, из первой строки
            if header_lines and header_lines[0].startswith("\ufeff"):
                header_lines[0] = header_lines[0].replace("\ufeff", "")

            if len(header_lines) < 2:
                return render(request, 'tests/import_questions_text.html', {'error': 'Неверный формат заголовка.'})

            if not header_lines[0].startswith("Предмет:") or not header_lines[1].startswith("Раздел:"):
                return render(request, 'tests/import_questions_text.html', {
                    'error': 'Неверный формат заголовков. Заголовки должны начинаться с "Предмет:" и "Раздел:"'
                })
            file_subject = header_lines[0].split(":", 1)[1].strip()
            file_section = header_lines[1].split(":", 1)[1].strip()

            # Находим блок с правильными ответами (ожидается, что он начинается со строки "Правильные ответы:")
            answer_block = None
            for block in blocks:
                if block.startswith("Правильные ответы:"):
                    answer_block = block
                    break
            if not answer_block:
                return render(request, 'tests/import_questions_text.html',
                              {'error': 'Блок "Правильные ответы:" не найден.'})
            # Фильтруем пустые строки в блоке правильных ответов
            answer_lines = [line.strip() for line in answer_block.splitlines()[1:] if line.strip()]

            # Остальные блоки (кроме заголовка и блока с ответами) – это блоки вопросов
            question_blocks = [block for block in blocks if block not in [blocks[0], answer_block]]

            parsed_questions = []
            for block in question_blocks:
                lines = block.splitlines()
                if len(lines) < 5:
                    continue  # пропускаем блоки, где меньше 5 строк (1 вопрос + 4 варианта)
                q_line = lines[0].strip()
                # Убираем ведущие цифры, точку и пробел, если они есть
                clean_q_line = re.sub(r'^\d+\.\s*', '', q_line)
                opts = []
                for opt_line in lines[1:5]:
                    # Убираем префикс типа "А)" или "В)"
                    parts = re.split(r'\)\s*', opt_line, maxsplit=1)
                    option_text = parts[1].strip() if len(parts) == 2 else opt_line.strip()
                    opts.append(option_text)
                parsed_questions.append({
                    'question_text': clean_q_line,
                    'options': opts,
                })

            # Проверка: количество строк с правильными ответами должно совпадать с количеством вопросов
            if len(answer_lines) != len(parsed_questions):
                error_msg = f"Количество правильных ответов ({len(answer_lines)}) не совпадает с количеством вопросов ({len(parsed_questions)})."
                return render(request, 'tests/import_questions_text.html', {'error': error_msg})

            # Сопоставляем правильные ответы с вопросами
            letter_map = {'A': 1, 'А': 1, 'B': 2, 'В': 2, 'C': 3, 'С': 3, 'D': 4, 'Д': 4}
            for i, ans in enumerate(answer_lines):
                ans = ans.strip()
                if not ans:
                    correct_option = 1
                else:
                    letter = ans[-1].upper()
                    correct_option = letter_map.get(letter, 1)
                parsed_questions[i]['correct_option'] = correct_option

            data = {
                'subject': file_subject,
                'section': file_section,
                'count': len(parsed_questions),
                'questions': parsed_questions,
            }
            # Сохраняем разобранные данные для этапа подтверждения
            request.session['import_questions_data'] = data
            return render(request, 'tests/import_questions_confirm.html', data)
    else:
        # GET-запрос: вывод формы загрузки файла
        return render(request, 'tests/import_questions_text.html')
